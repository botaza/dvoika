import logging
import random
import shutil
import os
import glob

from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from bot_token import BOT_TOKEN

logging.basicConfig(level=logging.INFO)

ADMIN_UID = 1049416300

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())


# ================= STATES =================
class Flow(StatesGroup):
    password = State()
    main = State()
    action = State()
    activity_decision = State()
    goal_decision = State()
    submit_activity = State()
    confirm_new_current = State()
    choose_from_list = State()


# ================= ADMIN NOTIFY =================
async def notify_admin(user_id: int, hashtag: str, text: str = ""):
    msg = f"{user_id} #{hashtag}"
    if text:
        msg += f"\n{text}"
    await bot.send_message(ADMIN_UID, msg)


# ================= HELPERS =================
def user_files(user_id):
    return {
        "h": f"h{user_id}.txt",
        "rt": f"{user_id}rt.txt",
        "p": f"{user_id}p.txt",
        "c": f"{user_id}c.txt",
    }


def read_lines(path):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return [l.strip() for l in f if l.strip()]


def write_lines(path, lines):
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def append_line(path, line):
    if os.path.exists(path):
        with open(path, "rb+") as f:
            f.seek(0, 2)
            if f.tell() > 0:
                f.seek(-1, 2)
                if f.read(1) != b"\n":
                    f.write(b"\n")
    with open(path, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def ensure_global_rt():
    if not os.path.exists("rt.txt"):
        open("rt.txt", "w", encoding="utf-8").close()


def emoji_numbers(n):
    emojis_1_10 = ["1️⃣","2️⃣","3️⃣","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]
    if n <= 10:
        return emojis_1_10[n-1]
    else:
        return f"{n}️⃣"


# ================= KEYBOARDS =================
def kb_main():
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("двойка основной", callback_data="main"))
    return kb


def kb_action():
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("Отправить активность", callback_data="submit"))
    kb.add(types.InlineKeyboardButton("Получить активность", callback_data="get"))
    kb.add(types.InlineKeyboardButton("Посмотреть список активностей", callback_data="list"))
    return kb


def kb_activity():
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("Выбросить", callback_data="discard"))
    kb.add(types.InlineKeyboardButton("Оставить", callback_data="keep"))
    return kb


def kb_goal():
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("Цель выполнена", callback_data="done"))
    kb.add(types.InlineKeyboardButton("Поменять активность", callback_data="change"))
    return kb


def kb_confirm_current():
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("Да", callback_data="yes"))
    kb.add(types.InlineKeyboardButton("Нет", callback_data="no"))
    return kb


def kb_list_menu():
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🎲 Выбрать случайно", callback_data="get"))
    kb.add(types.InlineKeyboardButton("Выбрать активность", callback_data="choose"))
    kb.add(types.InlineKeyboardButton("Удалить активности", callback_data="delete"))
    return kb


# ================= BIGBANG =================
@dp.message_handler(lambda m: m.text and m.text.lower() == "bigbang", state="*")
async def bigbang(message: types.Message, state: FSMContext):
    await state.finish()
    await state.reset_data()
    for file in glob.glob("*.txt"):
        if os.path.basename(file) != "rt.txt":
            os.remove(file)
    await message.answer("💥 Вселенная пересобрана.")
    await message.answer("Привет. Введи пароль: эмоцзи того, кому разрешен доступ")
    await Flow.password.set()


# ================= RESET =================
@dp.message_handler(commands=["reset"], state="*")
async def reset(message: types.Message, state: FSMContext):
    await state.finish()
    await state.reset_data()
    await message.answer("Состояние сброшено. Выбери режим:", reply_markup=kb_main())
    await Flow.main.set()


# ================= START =================
@dp.message_handler(commands=["start"], state="*")
async def start(message: types.Message, state: FSMContext):
    ensure_global_rt()
    await state.finish()
    await state.reset_data()
    uid = message.from_user.id
    await notify_admin(uid, "start")
    files = user_files(uid)
    p_tasks = read_lines(files["p"])
    if p_tasks:
        task = p_tasks[0]
        await message.answer(f"Ваша текущая активность:\n\n{task}")
        await message.answer("Выберите действие:", reply_markup=kb_goal())
        await Flow.goal_decision.set()
        return
    await message.answer("Привет. Введи пароль: эмоцзи того, кому разрешен доступ")
    await Flow.password.set()


# ================= PASSWORD =================
@dp.message_handler(state=Flow.password)
async def password(message: types.Message):
    if message.text not in ("🐱", "🦁"):
        await message.answer("Неверный пароль")
        return
    uid = message.from_user.id
    files = user_files(uid)
    open(files["h"], "a").close()
    ensure_global_rt()
    shutil.copy("rt.txt", files["rt"])
    await message.answer("Выбери режим", reply_markup=kb_main())
    await Flow.main.set()


# ================= MAIN =================
@dp.callback_query_handler(lambda c: c.data == "main", state=Flow.main)
async def main(cb: types.CallbackQuery):
    await cb.message.edit_text("Что делаем?", reply_markup=kb_action())
    await Flow.action.set()
    await cb.answer()


# ================= ACTION =================
@dp.callback_query_handler(lambda c: c.data in ["get", "list", "submit"], state=Flow.action)
async def action_stage(cb: types.CallbackQuery, state: FSMContext):
    uid = cb.from_user.id
    files = user_files(uid)
    if cb.data == "get":
        await get_activity(cb, state)
        return
    if cb.data == "list":
        tasks = read_lines(files["rt"])
        if not tasks:
            await cb.message.answer("Список активностей пуст.")
            await cb.message.answer("Выберите действие:", reply_markup=kb_action())
        else:
            text = "\n".join(f"{emoji_numbers(i+1)} {t}" for i, t in enumerate(tasks))
            await cb.message.answer(f"Список активностей:\n{text}")
            await cb.message.answer("Что делать дальше?", reply_markup=kb_list_menu())
        await cb.answer()
        return
    if cb.data == "submit":
        await cb.message.answer("Введите идею активности:")
        await Flow.submit_activity.set()
        await cb.answer()


# ================= LIST MENU HANDLER =================
@dp.callback_query_handler(lambda c: c.data in ["choose", "delete", "get"], state="*")
async def list_menu_handler(cb: types.CallbackQuery, state: FSMContext):
    uid = cb.from_user.id
    files = user_files(uid)

    if cb.data == "choose":
        await cb.message.answer("Введите номер активности, чтобы сделать её текущей:")
        await Flow.choose_from_list.set()

    elif cb.data == "delete":
        tasks = read_lines(files["rt"])
        if not tasks:
            await cb.message.answer("Список активностей пуст, нечего удалять.")
            await cb.message.answer("Выберите действие:", reply_markup=kb_action())
        else:
            text = "\n".join(f"{emoji_numbers(i+1)} {t}" for i, t in enumerate(tasks))
            await cb.message.answer(
                f"Список активностей:\n{text}\n\nВведите номера активностей для удаления через пробел или запятую:"
            )
            await Flow.choose_from_list.set()
            await state.update_data(delete_mode=True)

    elif cb.data == "get":
        await get_activity(cb, state)

    await cb.answer()


# ================= CHOOSE ACTIVITY =================
@dp.message_handler(state=Flow.choose_from_list)
async def choose_activity(message: types.Message, state: FSMContext):
    uid = message.from_user.id
    files = user_files(uid)
    data = await state.get_data()
    delete_mode = data.get("delete_mode", False)
    tasks = read_lines(files["rt"])

    if delete_mode:
        nums = message.text.replace(",", " ").split()
        to_delete = []
        for n in nums:
            if n.isdigit():
                i = int(n)
                if 1 <= i <= len(tasks):
                    to_delete.append(i-1)
        if not to_delete:
            await message.answer("Неверные номера. Попробуйте снова.")
            return
        deleted_tasks = []
        for idx in sorted(to_delete, reverse=True):
            deleted_tasks.append(tasks.pop(idx))
        write_lines(files["rt"], tasks)
        await message.answer(f"Удалено {len(deleted_tasks)} активностей:\n" + "\n".join(deleted_tasks))
        await state.update_data(delete_mode=False)
        await message.answer("Возвращаемся в главное меню.", reply_markup=kb_main())
        await Flow.main.set()
        return

    try:
        num = int(message.text)
        if not (1 <= num <= len(tasks)):
            raise ValueError
        chosen_task = tasks[num-1]
        tasks.pop(num-1)
        write_lines(files["rt"], tasks)
        write_lines(files["p"], [chosen_task])
        await notify_admin(uid, "got", chosen_task)
        await message.answer(f"Вы выбрали текущую активность:\n\n{chosen_task}", reply_markup=kb_goal())
        await Flow.goal_decision.set()
    except ValueError:
        await message.answer("Неверный номер, попробуйте снова.")


# ================= SUBMIT =================
@dp.message_handler(state=Flow.submit_activity)
async def submit_activity(message: types.Message, state: FSMContext):
    uid = message.from_user.id
    files = user_files(uid)
    text = message.text.strip()
    if not text:
        await message.answer("Пустая активность не может быть добавлена.")
        return
    append_line("rt.txt", text)
    append_line(files["rt"], text)
    await notify_admin(uid, "idea", text)
    await state.update_data(new_idea=text)
    await message.answer(
        "Активность добавлена. Сделать её текущей активностью?",
        reply_markup=kb_confirm_current()
    )
    await Flow.confirm_new_current.set()


# ================= CONFIRM NEW CURRENT =================
@dp.callback_query_handler(state=Flow.confirm_new_current)
async def confirm_new_current(cb: types.CallbackQuery, state: FSMContext):
    uid = cb.from_user.id
    data = await state.get_data()
    new_task = data.get("new_idea")
    files = user_files(uid)
    if cb.data == "yes":
        rt = read_lines(files["rt"])
        if new_task in rt:
            rt.remove(new_task)
        write_lines(files["rt"], rt)
        write_lines(files["p"], [new_task])
        await notify_admin(uid, "got", new_task)
        await cb.message.answer(f"Ваша текущая активность:\n\n{new_task}", reply_markup=kb_goal())
        await Flow.goal_decision.set()
    else:
        await cb.message.answer("Возвращаемся в главное меню.", reply_markup=kb_main())
        await Flow.main.set()
    await cb.answer()


# ================= GET ACTIVITY =================
async def get_activity(cb: types.CallbackQuery, state: FSMContext):
    uid = cb.from_user.id
    files = user_files(uid)
    tasks = read_lines(files["rt"])
    if not tasks:
        await cb.message.answer("Все выполнено. Ждём новую идею")
        await Flow.action.set()
        return
    task = random.choice(tasks)
    await state.update_data(task=task)
    await cb.message.answer(f"Активность:\n\n{task}", reply_markup=kb_activity())
    await notify_admin(uid, "got", task)
    await Flow.activity_decision.set()
    await cb.answer()


# ================= DISCARD / KEEP =================
@dp.callback_query_handler(state=Flow.activity_decision)
async def activity_decision(cb: types.CallbackQuery, state: FSMContext):
    uid = cb.from_user.id
    files = user_files(uid)
    task = (await state.get_data())["task"]
    if cb.data == "discard":
        await notify_admin(uid, "discarded", task)
        rt = read_lines(files["rt"])
        if task in rt:
            rt.remove(task)
        write_lines(files["rt"], rt)
        await get_activity(cb, state)
        return
    if cb.data == "keep":
        await notify_admin(uid, "keep", task)
        rt = read_lines(files["rt"])
        if task in rt:
            rt.remove(task)
        write_lines(files["rt"], rt)
        write_lines(files["p"], [task])
        await cb.message.answer(f"Ваша активность:\n\n{task}")
        await cb.message.answer("Выберите действие:", reply_markup=kb_goal())
        await Flow.goal_decision.set()
    await cb.answer()


# ================= GOAL =================
@dp.callback_query_handler(state=Flow.goal_decision)
async def goal(cb: types.CallbackQuery, state: FSMContext):
    uid = cb.from_user.id
    files = user_files(uid)
    p_tasks = read_lines(files["p"])
    if not p_tasks:
        return
    old_task = p_tasks[0]
    if cb.data == "done":
        completed = read_lines(files["c"])
        completed.append(old_task)
        write_lines(files["c"], completed)
        write_lines(files["p"], [])
        await notify_admin(uid, "completed", old_task)
        await give_new_activity(cb, state, notify_new=True)
    elif cb.data == "change":
        rt = read_lines(files["rt"])
        rt.append(old_task)
        write_lines(files["rt"], rt)
        write_lines(files["p"], [])
        await notify_admin(uid, "changed", old_task)
        await give_new_activity(cb, state, notify_new=True)
    await cb.answer()


# ================= GIVE NEW =================
async def give_new_activity(cb: types.CallbackQuery, state: FSMContext, notify_new=False):
    uid = cb.from_user.id
    files = user_files(uid)
    rt = read_lines(files["rt"])
    if not rt:
        await cb.message.answer("Все выполнено. Ждём новую идею")
        await Flow.action.set()
        return
    task = random.choice(rt)
    rt.remove(task)
    write_lines(files["rt"], rt)
    write_lines(files["p"], [task])
    await cb.message.answer(f"Новая активность:\n\n{task}")
    await cb.message.answer("Выберите действие:", reply_markup=kb_goal())
    if notify_new:
        await notify_admin(uid, "got", task)
    await Flow.goal_decision.set()


# ================= RUN =================
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
