from flask import Flask, request, jsonify
import hashlib
import time
import jwt
import os
import redis

app = Flask(__name__)

# 从环境变量读取
SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key-change-this')
redis_client = redis.from_url(os.environ.get('REDIS_URL'))

# 有效的卡密（可以存Redis或代码里）
VALID_KEYS = {
    "VIP-2024-ABCD": {"max_uses": 1, "expiry": 1735689600},
}

@app.route('/verify', methods=['POST'])
def verify():
    data = request.json
    card_key = data.get('key')
    user_id = data.get('userId')
    client_timestamp = request.headers.get('X-Timestamp', 0)
    
    # 验证时间戳
    if abs(time.time() - int(client_timestamp)) > 60:
        return jsonify({"success": False, "message": "请求超时"})
    
    # 验证卡密
    if card_key not in VALID_KEYS:
        return jsonify({"success": False, "message": "卡密无效"})
    
    # 检查是否已使用
    used = redis_client.get(f"used:{card_key}")
    if used:
        return jsonify({"success": False, "message": "卡密已被使用"})
    
    # 标记已使用
    redis_client.setex(f"used:{card_key}", 86400, user_id)  # 24小时过期
    
    # 生成token
    token = jwt.encode({
        'user_id': user_id,
        'exp': time.time() + 3600
    }, SECRET_KEY, algorithm='HS256')
    
    return jsonify({"success": True, "message": "验证成功", "token": token})

@app.route('/heartbeat', methods=['POST'])
def heartbeat():
    token = request.json.get('token')
    try:
        jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        return jsonify({"success": True})
    except:
        return jsonify({"success": False}), 403

# Vercel需要
app = app

if __name__ == '__main__':
    app.run()
