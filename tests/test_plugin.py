"""The plugin as each harness loads it: skills, links, builds, adapters, and pstack coverage."""
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build  # noqa: E402

SKILLS = sorted((ROOT / "src" / "skills").glob("*/SKILL.md"))
PSTACK = Path(os.environ.get("PSTACK_SRC", ROOT / ".cache" / "cursor-plugins" / "harness" / "pstack" / "claude-code"))
HAVE_PSTACK = (PSTACK / "skills" / "poteto-mode" / "SKILL.md").exists()


def md_files():
    for base in (ROOT / "src", ROOT / "docs"):
        yield from base.rglob("*.md")
    yield ROOT / "README.md"


class SkillTest(unittest.TestCase):
    def test_every_skill_has_name_matching_folder_and_a_description(self):
        self.assertGreaterEqual(len(SKILLS), 2)
        for p in SKILLS:
            fields, body = build.split_frontmatter(p.read_text(encoding="utf-8"))
            self.assertEqual(fields.get("name", "").strip('"'), p.parent.name, p)
            desc = fields.get("description", "").strip('"')
            self.assertTrue(20 < len(desc) <= 1024, f"{p}: description length {len(desc)}")
            self.assertNotIn("<", desc, f"{p}: angle brackets in description")
            self.assertTrue(body.strip(), p)

    def test_relative_links_resolve(self):
        bad = []
        for p in md_files():
            if not p.exists():
                continue
            for target in re.findall(r"\]\(([^)#\s]+)", p.read_text(encoding="utf-8")):
                if "://" in target or target.startswith("mailto:"):
                    continue
                if not (p.parent / target).exists():
                    bad.append(f"{p.relative_to(ROOT)} -> {target}")
        self.assertEqual(bad, [])

    def test_backticked_relative_paths_in_skills_resolve(self):
        bad = []
        # Skills point at files relative to the installed plugin, so check each build.
        for harness in ("claude-code", "antigravity"):
            for p in sorted((ROOT / "dist" / harness / "skills").glob("*/SKILL.md")):
                for target in re.findall(r"`(\.\./[^`\s]+|playbooks/[^`\s]+\.md|scripts/[^`\s]+\.py)`", p.read_text(encoding="utf-8")):
                    if not (p.parent / target).exists():
                        bad.append(f"{p.relative_to(ROOT)} -> {target}")
        self.assertEqual(bad, [])

    def test_no_long_dashes_in_agent_facing_prose(self):
        for p in list(md_files()):
            if p.exists():
                self.assertNotIn("—", p.read_text(encoding="utf-8"), p)


class BuildTest(unittest.TestCase):
    def test_dist_is_in_sync_with_src(self):
        r = subprocess.run([sys.executable, str(ROOT / "scripts" / "build.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_check_fails_when_dist_is_stale(self):
        with tempfile.TemporaryDirectory() as t:
            a, b = Path(t) / "a", Path(t) / "b"
            build.build(a)
            build.build(b)
            self.assertEqual(build.same_tree(a, b), [])
            (b / "claude-code" / "skills" / "task-state" / "SKILL.md").write_text("changed", encoding="utf-8")
            self.assertEqual(build.same_tree(a, b), ["claude-code/skills/task-state/SKILL.md: differs"])

    def test_manifests(self):
        cc = json.loads((ROOT / "dist/claude-code/.claude-plugin/plugin.json").read_text(encoding="utf-8"))
        ag = json.loads((ROOT / "dist/antigravity/plugin.json").read_text(encoding="utf-8"))
        meta = json.loads((ROOT / "stack.json").read_text(encoding="utf-8"))
        for m in (cc, ag):
            self.assertEqual((m["name"], m["version"]), (meta["name"], meta["version"]))
        self.assertIn("displayName", ag)
        mk = json.loads((ROOT / ".claude-plugin/marketplace.json").read_text(encoding="utf-8"))
        self.assertEqual(mk["plugins"][0]["source"], "./dist/claude-code")

    def test_agents_per_harness(self):
        for name in ("iskandar-agent",):
            cc, _ = build.split_frontmatter((ROOT / "dist/claude-code/agents" / f"{name}.md").read_text(encoding="utf-8"))
            ag, _ = build.split_frontmatter((ROOT / "dist/antigravity/agents" / f"{name}.md").read_text(encoding="utf-8"))
            self.assertNotIn("tools", cc, "Claude agents inherit every tool")
            tools = [t.strip() for t in ag["tools"].strip("[]").split(",")]
            self.assertEqual(sorted(tools), sorted(build.ANTIGRAVITY_TOOLS))
            self.assertIn(ag["model"], ("inherit", "flash", "pro"))
            json.loads(ag["description"])  # quoted, so YAML cannot misread a colon

    def test_antigravity_tools_are_the_ones_the_adapter_documents(self):
        adapter = (ROOT / "docs/harness/antigravity.md").read_text(encoding="utf-8")
        for t in build.ANTIGRAVITY_TOOLS:
            self.assertIn(f"`{t}`", adapter, t)

    def test_claude_hook_runs_quietly_outside_a_repo(self):
        hook = json.loads((ROOT / "dist/claude-code/hooks/hooks.json").read_text(encoding="utf-8"))
        cmd = hook["hooks"]["SessionStart"][0]["hooks"][0]["command"]
        cmd = cmd.replace("${CLAUDE_PLUGIN_ROOT}", str(ROOT / "dist/claude-code")).replace("python3", sys.executable)
        with tempfile.TemporaryDirectory() as t:
            r = subprocess.run(cmd, shell=True, cwd=t, capture_output=True, text=True)
        self.assertEqual((r.returncode, r.stdout, r.stderr), (0, "", ""))


@unittest.skipUnless(HAVE_PSTACK, "pstack not fetched: python3 scripts/fetch_pstack.py")
class PstackTest(unittest.TestCase):
    def test_every_pstack_skill_named_in_iskandar_mode_exists(self):
        mode = (ROOT / "src/skills/iskandar-mode/SKILL.md").read_text(encoding="utf-8")
        ours = {p.parent.name for p in SKILLS}
        named = set(re.findall(r"\*\*([a-z][a-z0-9-]+)\*\* (?:skill|for|across|and|when|before|to|after)", mode))
        named |= set(re.findall(r"the \*\*([a-z][a-z0-9-]+)\*\* skill", mode))
        theirs = {p.parent.name for p in (PSTACK / "skills").glob("*/SKILL.md")}
        self.assertGreater(len(named), 15, named)
        self.assertEqual(sorted(named - theirs - ours), [])

    def test_every_poteto_playbook_is_routed(self):
        mode = (ROOT / "src/skills/iskandar-mode/SKILL.md").read_text(encoding="utf-8")
        poteto = (PSTACK / "skills/poteto-mode/SKILL.md").read_text(encoding="utf-8")
        section = poteto.split("## Playbooks", 1)[1]
        playbooks = re.findall(r"^- \*\*(.+?)\.\*\*", section, re.M)
        self.assertGreater(len(playbooks), 20)
        short = {"Authoring or modifying a skill": "Authoring a skill", "Multi-phase or multi-PR plan": "Multi-phase plan",
                 "Worktree and simulator cleanup": "Worktree cleanup"}
        missing = [p for p in playbooks if short.get(p, p) not in mode]
        self.assertEqual(missing, [], "iskandar-mode must route every poteto-mode playbook")

    def test_antigravity_adapter_covers_every_name_pstacks_claude_adapter_maps(self):
        cc = (PSTACK / "docs/harness/claude-code.md").read_text(encoding="utf-8")
        ag = (ROOT / "docs/harness/antigravity.md").read_text(encoding="utf-8")
        names = set()
        for section in ("## Tools", "## Subagent fields", "## Paths"):
            body = cc.split(section, 1)[1].split("\n## ", 1)[0]
            for row in re.findall(r"^\| (.+?) \|", body, re.M):
                if row.strip() in ("Cursor", "---"):
                    continue
                names.update(re.findall(r"`([^`]+)`", row) or [row.strip()])
        missing = sorted(n for n in names if n not in ag)
        self.assertEqual(missing, [], "add these Cursor names to docs/harness/antigravity.md")

    def test_pstack_antigravity_build(self):
        with tempfile.TemporaryDirectory() as t:
            out = Path(t) / "pstack"
            self.assertEqual(build.pstack_antigravity(PSTACK, out), 0)
            mode = (out / "skills/poteto-mode/SKILL.md").read_text(encoding="utf-8")
            self.assertIn("In Antigravity, read `~/.gemini/config/plugins/iskandar-stack/docs/harness/antigravity.md`", mode)
            for a in (out / "agents").glob("*.md"):
                fields, _ = build.split_frontmatter(a.read_text(encoding="utf-8"))
                self.assertIn("tools", fields, a)
            self.assertFalse((out / ".claude-plugin").exists())
            self.assertEqual(json.loads((out / "plugin.json").read_text(encoding="utf-8"))["name"], "pstack")

    def test_pstack_root_finds_each_harness_install(self):
        script = ROOT / "src/skills/iskandar-mode/scripts/pstack_root.py"
        for rel in (".claude/plugins/cache/cursor-plugins/pstack/0.15.36", ".gemini/config/plugins/pstack"):
            with tempfile.TemporaryDirectory() as home:
                target = Path(home) / rel / "skills" / "poteto-mode"
                target.mkdir(parents=True)
                (target / "SKILL.md").write_text("x", encoding="utf-8")
                env = {**os.environ, "ISKANDAR_HOME": home}
                env.pop("PSTACK_ROOT", None)
                r = subprocess.run([sys.executable, str(script)], env=env, capture_output=True, text=True)
                self.assertEqual(r.returncode, 0, r.stderr)
                self.assertEqual(Path(r.stdout.strip()), (Path(home) / rel).resolve())
        with tempfile.TemporaryDirectory() as home:
            env = {**os.environ, "ISKANDAR_HOME": home}
            env.pop("PSTACK_ROOT", None)
            r = subprocess.run([sys.executable, str(script)], env=env, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1)


if __name__ == "__main__":
    unittest.main()
