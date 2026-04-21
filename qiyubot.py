from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
import requests
import time
import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

# ========== 配置 ==========
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_KEY = os.getenv("QIYU_API_KEY")

if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError("Missing TELEGRAM_BOT_TOKEN in .env")

if not API_KEY:
    raise RuntimeError("Missing QIYU_API_KEY in .env")

COZE_TOKEN = f"Bearer {API_KEY}"
COZE_BOT_ID = "7629205761092419610"

# ========== 扣子 API ==========
def call_coze(user_id, message):
    """调用扣子Bot"""
    url = "https://api.coze.cn/v3/chat"
    headers = {
        "Authorization": COZE_TOKEN,
        "Content-Type": "application/json"
    }
    data = {
        "bot_id": COZE_BOT_ID,
        "user_id": user_id,
        "stream": False,
        "additional_messages": [
            {"role": "user", "content": message, "content_type": "text"}
        ]
    }
    
    # 发起对话
    resp = requests.post(url, headers=headers, json=data)
    result = resp.json()
    
    if result.get("code") != 0:
        return "扣子API调用失败"
    
    chat_id = result["data"]["id"]
    conversation_id = result["data"]["conversation_id"]
    
    # 等待处理完成
    time.sleep(3)
    
    # 获取回复
    msg_url = f"https://api.coze.cn/v3/chat/message/list?conversation_id={conversation_id}&chat_id={chat_id}"
    msg_resp = requests.get(msg_url, headers={"Authorization": COZE_TOKEN})
    msg_result = msg_resp.json()
    
    # 提取assistant的回复
    if msg_result.get("data"):
        for msg in msg_result["data"]:
            if msg.get("role") == "assistant" and msg.get("type") == "answer":
                content = msg.get("content", "")
                # 如果content是JSON字符串，需要解析
                if isinstance(content, str):
                    try:
                        import json
                        parsed = json.loads(content)
                        # 如果解析成功，取text字段
                        if isinstance(parsed, dict) and "text" in parsed:
                            return parsed["text"]
                    except:
                        pass
                return content
    
    return "无回复"

# ========== Telegram Handlers ==========
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理收到的消息"""
    user_id = str(update.message.from_user.id)
    text = update.message.text
    
    print(f"收到消息: {text}")
    
    # 调用扣子API
    reply = call_coze(user_id, text)
    
    # 回复用户
    await update.message.reply_text(reply)
    print(f"回复: {reply}")

# ========== 启动 ==========
if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    
    # 监听所有文本消息
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("Bot启动了，去Telegram发消息试试")
    app.run_polling()