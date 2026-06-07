"""本地单元测试：验证 parse_curl + classify 逻辑
不需要真实 hitun.io 账号，本地就能跑
"""
import sys
sys.path.insert(0, '/Users/wanglingwei/Documents/hitun-checkin-action')

from main import parse_curl, classify

# ========== Test 1: Chrome DevTools 复制出的真实格式 ==========
real_curl = r"""curl 'https://hitun.io/user/checkin' \
  -H 'authority: hitun.io' \
  -H 'accept: application/json, text/javascript, */*; q=0.01' \
  -H 'accept-language: zh-CN,zh;q=0.9' \
  -H 'cookie: cf_clearance=abc123def; PHPSESSID=xyz789; uid=12345' \
  -H 'origin: https://hitun.io' \
  -H 'referer: https://hitun.io/user' \
  -H 'user-agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36' \
  -H 'x-requested-with: XMLHttpRequest' \
  --data-raw '' \
  --compressed"""

print("=== Test 1: Chrome DevTools style (多行 + \ 续行) ===")
spec = parse_curl(real_curl)
assert spec['method'] == 'POST', f"method={spec['method']}"
assert spec['url'] == 'https://hitun.io/user/checkin', f"url={spec['url']}"
assert spec['cookies']['cf_clearance'] == 'abc123def'
assert spec['cookies']['PHPSESSID'] == 'xyz789'
assert spec['cookies']['uid'] == '12345'
assert spec['body'] == ''
print(f"  ✓ method={spec['method']}, cookies={list(spec['cookies'].keys())}")
print(f"  ✓ body={repr(spec['body'])}, headers={len(spec['headers'])} 个")

# ========== Test 2: 简写形式（-b + -X） ==========
simple_curl = "curl -X POST 'https://hitun.io/user/checkin' -b 'cf_clearance=abc; PHPSESSID=xyz' -H 'User-Agent: test'"
print("\n=== Test 2: Simple style (单行 + -b) ===")
spec = parse_curl(simple_curl)
assert spec['method'] == 'POST'
assert spec['url'] == 'https://hitun.io/user/checkin'
assert spec['cookies']['cf_clearance'] == 'abc'
assert spec['cookies']['PHPSESSID'] == 'xyz'
print(f"  ✓ method={spec['method']}, cookies={spec['cookies']}")

# ========== Test 3: 带 body 的 POST ==========
body_curl = "curl -X POST 'https://hitun.io/api/foo' -H 'Cookie: a=1' --data-raw '{\"x\":1}'"
print("\n=== Test 3: POST with body ===")
spec = parse_curl(body_curl)
assert spec['method'] == 'POST'
assert spec['body'] == '{"x":1}', f"body={spec['body']}"
print(f"  ✓ body={spec['body']}")

# ========== Test 4: classify 各种响应 ==========
print("\n=== Test 4: classify 各种响应 ===")
cases = [
    ('{"ret":1,"msg":"签到成功,获得100MB"}', 200, True, '签到成功'),
    ('{"ret":0,"msg":"今日已签到"}', 200, True, '已签到（视为成功）'),
    ('{"ret":0,"msg":"未登录"}', 200, False, 'Cookie 失效'),
    ('{"ret":0,"msg":"邮箱未注册"}', 200, False, 'Cookie 失效'),
    ('<html>Just a moment...</html>', 200, False, 'Cloudflare challenge'),
    ('Forbidden', 403, False, '403 拒绝'),
    ('{"ret":0,"msg":"未知错误"}', 200, False, '业务失败'),
    ('server error', 500, False, '服务器异常'),
    ('{"ret":1,"msg":"ok"}', 200, True, 'ret=1 通用成功'),
]
for body, status, expected_ok, label in cases:
    desc, ok = classify(body, status)
    assert ok == expected_ok, f"[{label}] classify returned ok={ok}, expected {expected_ok}\ndesc={desc}"
    print(f"  ✓ [{status}] {label} → ok={ok}")

# ========== Test 5: 边界 ==========
print("\n=== Test 5: Edge cases ===")
for bad in ["", "garbage", "curl", "curl 'https://hitun.io'"]:
    try:
        parse_curl(bad)
        # 没抛异常也行，只要不崩
        print(f"  · {repr(bad)[:30]}: 不报错（宽松模式）")
    except Exception as e:
        print(f"  ✓ {repr(bad)[:30]}: 抛错 → {type(e).__name__}: {e}")

print("\n" + "=" * 50)
print("🎉 全部测试通过")
