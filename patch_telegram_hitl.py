import os

filepath = r'c:\Users\LENOVO\Ninoclaw\telegram_bot.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add imports
if "InlineKeyboardMarkup" not in content:
    content = content.replace("from telegram import Update", "from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton")

if "CallbackQueryHandler" not in content:
    content = content.replace("from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes", "from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes")

# 2. Intercept [REQUIRES_CONFIRMATION] in handle_message
target_exec = """            result = await execute_tool(tool_name, tool_args, user_id, task_manager)
            step_results.append(result)"""

replacement_exec = """            result = await execute_tool(tool_name, tool_args, user_id, task_manager)
            
            if isinstance(result, str) and result.startswith("[REQUIRES_CONFIRMATION]"):
                import json
                try:
                    payload_str = result.replace("[REQUIRES_CONFIRMATION]", "").strip()
                    payload = json.loads(payload_str)
                    
                    # Store pending action
                    memory.set_user_data(user_id, "pending_tool", payload)
                    
                    keyboard = [
                        [
                            InlineKeyboardButton("Approve ✅", callback_data="hitl_approve"),
                            InlineKeyboardButton("Reject ❌", callback_data="hitl_reject"),
                        ]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    cmd_info = payload.get('arguments', {}).get('command', '')
                    warning_msg = f"⚠️ *Action Required!*\n\nI need permission to run `{payload.get('name')}`."
                    if cmd_info:
                        warning_msg += f"\\n\\nCommand: `{cmd_info}`"
                    
                    await update.message.reply_text(warning_msg, reply_markup=reply_markup, parse_mode="Markdown")
                    
                    skip_final_summarization = True
                    step_results.append(f"Paused execution waiting for user permission to run {payload.get('name')}.")
                    break
                except Exception as e:
                    result = f"❌ Failed to parse confirmation request: {e}"
            
            step_results.append(result)"""

if target_exec in content:
    content = content.replace(target_exec, replacement_exec)
else:
    print("Warning: target_exec not found exactly.")
    # Let's try a looser replacement if needed, but it should be exact.

# 3. Add CallbackQueryHandler function and register it
target_create_bot = "def create_bot(token):"

callback_func = """
async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    if query.data == "hitl_approve":
        pending = memory.get_user_data(user_id, "pending_tool", None)
        if not pending:
            await query.edit_message_text(text="⚠️ Approval expired or not found.")
            return
            
        tool_name = pending.get("name")
        tool_args = pending.get("arguments", {})
        
        await query.edit_message_text(text=f"✅ Approved. Executing `{tool_name}`...")
        
        # Bypass confirmation requirement
        tool_args["_confirmed"] = True
        
        try:
            result = await execute_tool(tool_name, tool_args, user_id, task_manager)
            
            # Inject result into memory
            memory.add_message(user_id, "user", f"[System] User approved execution of {tool_name}. Result:\\n{str(result)[:2000]}\\n\\nPlease continue.")
            memory.set_user_data(user_id, "pending_tool", None)
            
            await context.bot.send_message(
                chat_id=update.effective_chat.id, 
                text=f"🔧 **Tool Executed**\\n\\n```\\n{str(result)[:1000]}\\n```\\n\\n*Type 'continue' to let me proceed with the next steps.*",
                parse_mode="Markdown"
            )
        except Exception as e:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"❌ Execution failed: {e}")
            
    elif query.data == "hitl_reject":
        pending = memory.get_user_data(user_id, "pending_tool", None)
        tool_name = pending.get("name") if pending else "unknown tool"
        
        await query.edit_message_text(text=f"❌ Rejected `{tool_name}`.")
        memory.add_message(user_id, "user", f"[System] User REJECTED execution of {tool_name}. You must find an alternative approach or stop.")
        memory.set_user_data(user_id, "pending_tool", None)
        
        await context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text="*Action cancelled. Type 'continue' or send new instructions to proceed.*",
            parse_mode="Markdown"
        )

def create_bot(token):"""

if target_create_bot in content:
    content = content.replace(target_create_bot, callback_func)

target_add_handler = "app.add_handler(CommandHandler(\"jobsearch_interval\", set_jobsearch_interval))"
replacement_add_handler = """app.add_handler(CommandHandler("jobsearch_interval", set_jobsearch_interval))
    
    # Callback Handlers
    app.add_handler(CallbackQueryHandler(handle_callback_query))"""

if target_add_handler in content:
    content = content.replace(target_add_handler, replacement_add_handler)


with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("SUCCESS: Patched telegram_bot.py")

