"""Real stdio MCP client for the configured upstream server, without an LLM API.

Allows the current task to use MCP before the desktop app refreshes its tool list.
The host addon must already be running via start_blender.ps1.
"""
import argparse
import asyncio
import base64
from datetime import datetime, timezone, timedelta
import hashlib
import json
import os
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]

async def main():
    p = argparse.ArgumentParser()
    p.add_argument('--list', action='store_true')
    p.add_argument('--batch', type=Path)
    p.add_argument('--code', type=Path)
    p.add_argument('--report', type=Path, required=True)
    args = p.parse_args()
    env = dict(os.environ)
    env.update(DISABLE_TELEMETRY='true', BLENDER_MCP_DISABLE_TELEMETRY='true',
               PYTHONUTF8='1', APPDATA=str(ROOT/'runtime'/'mcp_profile'),
               TMP=str(ROOT/'runtime'/'tmp'), TEMP=str(ROOT/'runtime'/'tmp'))
    for key in ['APPDATA', 'TMP']:
        Path(env[key]).mkdir(parents=True, exist_ok=True)
    params = StdioServerParameters(
        command=str(ROOT/'.venv'/'Scripts'/'mcp-for-blender.exe'),
        args=['--host', '127.0.0.1', '--port', '19876'], env=env,
        cwd=str(ROOT))
    args.report.parent.mkdir(parents=True, exist_ok=True)
    log = args.report.with_suffix('.stderr.log')
    report = {'utc': datetime.now(timezone.utc).isoformat(),
              'transport': 'MCP stdio -> upstream mcp-for-blender -> local Blender addon',
              'calls': []}
    calls = json.loads(args.batch.read_text(encoding='utf-8')) if args.batch else []
    if args.code:
        calls.append({'tool': 'execute_blender_code', 'arguments': {
            'code': args.code.read_text(encoding='utf-8')}})
    with log.open('w', encoding='utf-8') as err:
        async with stdio_client(params, errlog=err) as (read, write):
            async with ClientSession(read, write, read_timeout_seconds=timedelta(seconds=300)) as session:
                initialized = await session.initialize()
                report['server'] = initialized.serverInfo.model_dump()
                if args.list:
                    result = await session.list_tools()
                    report['tools'] = [t.model_dump() for t in result.tools]
                    print(json.dumps({'tools': [t.name for t in result.tools]}, ensure_ascii=False))
                for i, call in enumerate(calls):
                    result = await session.call_tool(call['tool'], call.get('arguments', {}))
                    record = {'tool': call['tool'], 'isError': result.isError, 'content': []}
                    for j, block in enumerate(result.content):
                        if block.type == 'image':
                            data = base64.b64decode(block.data)
                            path = args.report.parent/f'{args.report.stem}-{i}-{j}.png'
                            path.write_bytes(data)
                            record['content'].append({'type': 'image', 'path': str(path),
                                                      'sha256': hashlib.sha256(data).hexdigest()})
                        else:
                            record['content'].append(block.model_dump())
                    report['calls'].append(record)
                    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
                    summary = {**record, 'content': []}
                    for block in record['content']:
                        brief = dict(block)
                        if len(brief.get('text', '')) > 5000:
                            full = brief['text']
                            brief['text'] = full[:350] + '\n[Full output retained in report]\n' + full[-2200:]
                        summary['content'].append(brief)
                    print(json.dumps(summary, ensure_ascii=False), flush=True)
                    text_failure = any(c.get('type') == 'text' and c.get('text', '').startswith(
                        ('Error ', 'Error:', 'Rejected by safe mode')) for c in record['content'])
                    if result.isError or text_failure:
                        raise RuntimeError(f'MCP tool failed: {call["tool"]}')
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')

if __name__ == '__main__':
    asyncio.run(main())
