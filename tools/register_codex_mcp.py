"""Append one verified MCP entry; preserve all other Codex settings exactly."""
import hashlib
import json
from pathlib import Path
import tomllib

ROOT = Path(__file__).resolve().parents[1]
config = Path.home()/'.codex'/'config.toml'
before_bytes = config.read_bytes()
before = tomllib.loads(before_bytes.decode('utf-8-sig'))
name = 'blender_zurich'
if name in before.get('mcp_servers', {}):
    raise SystemExit('Entry already exists; inspect before changing it')
addition = '''

# ZurichWorld local Blender bridge. Configured 2026-09-21.
[mcp_servers.blender_zurich]
command = "F:/MyWorld/ZurichWorld/.venv/Scripts/mcp-for-blender.exe"
args = ["--host", "127.0.0.1", "--port", "19876"]
cwd = "F:/MyWorld/ZurichWorld"
enabled = true
startup_timeout_sec = 30
tool_timeout_sec = 300
enabled_tools = ["get_addon_status", "disable_telemetry", "get_scene_info", "get_object_info", "get_viewport_screenshot", "execute_blender_code", "describe_node_type", "bpy_api_lookup", "export_scene", "get_polyhaven_categories", "search_polyhaven_assets", "get_polyhaven_asset_preview", "download_polyhaven_asset", "set_texture", "get_polyhaven_status"]

[mcp_servers.blender_zurich.env]
DISABLE_TELEMETRY = "true"
BLENDER_MCP_DISABLE_TELEMETRY = "true"
PYTHONUTF8 = "1"
APPDATA = "F:/MyWorld/ZurichWorld/runtime/mcp_profile"
TMP = "F:/MyWorld/ZurichWorld/runtime/tmp"
TEMP = "F:/MyWorld/ZurichWorld/runtime/tmp"
'''
new_bytes = before_bytes + addition.encode('utf-8')
after = tomllib.loads(new_bytes.decode('utf-8-sig'))
entry = after['mcp_servers'].pop(name)
assert before == after, 'Unrelated configuration changed'
assert config.read_bytes() == before_bytes, 'Configuration changed concurrently'
temp = config.with_name('config.toml.zurich-new')
temp.write_bytes(new_bytes)
temp.replace(config)
report = {'config_path':str(config),'entry':name,'enabled':entry['enabled'],
          'unrelated_settings_preserved':True,
          'before_sha256':hashlib.sha256(before_bytes).hexdigest(),
          'after_sha256':hashlib.sha256(new_bytes).hexdigest(),
          'reason':'Installed legacy Codex CLI rejects existing max effort. Used TOML-preserving append; reasoning setting unchanged.'}
(ROOT/'runtime'/'mcp_registration.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))

