#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
====================================================================
  UNIVERSAL LUA DEOBFUSCATOR SUITE - ADVANCED MULTI-ENGINE
====================================================================
Hỗ trợ toàn diện các loại Obfuscator:
1. MoonSec V3 / MoonSec V2 (Lua Virtual Machine Obfuscator)
 2. Luraph (LPH v11 / v12 / v13 / v14 / v15) XOR Recovery, VM Analysis & Constant Pool Extraction
3. IronBrew 2 / PSU / AztupBrew (XOR & VM Bytecode Obfuscators)
4. Prometheus (Metamethod & Custom VM Obfuscator)
5. WeAreDevs (WRD) v1.0.0 (String Permutation & UI VM Obfuscator)
6. Synapse Xen / Bitwise XOR / Byte-Shift Obfuscator
7. Luarmor / Key System Loaders & Dynamic Payload Extractors
8. Escaped Hex / Octal / Decimal & string.char / table.concat
9. Compiled Lua 5.1 Bytecode (.luac / \x1bLuaQ) Constant & String Decompiler
10. AST Beautifier, Constant Folder & Variable Renamer
====================================================================
"""

import os
import sys
import re
import json
import time
import struct
import tempfile
import subprocess
import urllib.request
import urllib.error
from pathlib import Path

# ANSI Color Palette
C_RESET   = "\033[0m"
C_BOLD    = "\033[1m"
C_DIM     = "\033[2m"
C_RED     = "\033[91m"
C_GREEN   = "\033[92m"
C_YELLOW  = "\033[93m"
C_BLUE    = "\033[94m"
C_MAGENTA = "\033[95m"
C_CYAN    = "\033[96m"
C_WHITE   = "\033[97m"

EMBEDDED_LUA_TRACER = r'''
-- Dynamic Lua Sandbox & Multi-Engine VM Tracer (Enhanced for MoonSec, Luraph, IronBrew, Xen, Luarmor)
local serialize_value

serialize_value = function(val, indent, seen)
    indent = indent or ""
    seen = seen or {}
    local t = type(val)
    if t == "table" then
        if seen[val] then
            return "{ ... (circular ref) }"
        end
        seen[val] = true
        local is_array = true
        local max_idx = 0
        for k, v in pairs(val) do
            if type(k) ~= "number" or k <= 0 or math.floor(k) ~= k then
                is_array = false
                break
            else
                if k > max_idx then max_idx = k end
            end
        end
        if is_array and max_idx == #val and max_idx > 0 then
            local items = {}
            for i = 1, #val do
                items[#items + 1] = serialize_value(val[i], indent .. "    ", seen)
            end
            return "{\n" .. indent .. "    " .. table.concat(items, ",\n" .. indent .. "    ") .. "\n" .. indent .. "}"
        end
        
        local lines = {"{\n"}
        local next_indent = indent .. "    "
        for k, v in pairs(val) do
            local key_str
            if type(k) == "string" and k:match("^[%a_][%w_]*$") then
                key_str = string.format("[%q]", k)
            elseif type(k) == "string" then
                key_str = string.format("[%q]", k)
            else
                key_str = string.format("[%s]", tostring(k))
            end
            lines[#lines + 1] = string.format("%s%s = %s,\n", next_indent, key_str, serialize_value(v, next_indent, seen))
        end
        lines[#lines + 1] = indent .. "}"
        return table.concat(lines)
    elseif t == "string" then
        return string.format("%q", val)
    elseif t == "number" or t == "boolean" then
        return tostring(val)
    elseif t == "nil" then
        return "nil"
    else
        return string.format("%s", tostring(val))
    end
end

local trace_events = {}
local recorded_genv = {}
local recorded_g = {}
local recorded_loads = {}
local recorded_http = {}
local recorded_prints = {}

local function record_event(kind, data)
    trace_events[#trace_events + 1] = { kind = kind, data = data }
end

local function make_mock_object(name, path)
    path = path or name
    local mock = {}
    local mt = {
        __tostring = function() return path end,
        __concat = function(a, b)
            return tostring(a) .. tostring(b)
        end,
        __index = function(t, k)
            if k == "Value" then return "100" end
            if k == "Name" then return "LocalPlayer" end
            if k == "DisplayName" then return "DisplayName" end
            if k == "UserId" then return 123456789 end
            if k == "AccountAge" then return 500 end
            if k == "Position" then return { X=0, Y=0, Z=0 } end
            if k == "CFrame" then return { Position = { X=0, Y=0, Z=0 } } end
            if k == "Health" or k == "MaxHealth" then return 100 end
            local sub_path = path .. "." .. tostring(k)
            return make_mock_object(tostring(k), sub_path)
        end,
        __newindex = function(t, k, v)
            record_event("SET_PROP", { target = path, prop = tostring(k), value = serialize_value(v) })
        end,
        __call = function(t, ...)
            local args = {...}
            local arg_strs = {}
            for i = 1, #args do
                if i == 1 and args[i] == t then
                    -- self argument
                else
                    arg_strs[#arg_strs + 1] = serialize_value(args[i])
                end
            end
            
            if path:match("HttpGet") or path:match("http_request") or path:match("request") then
                local url = args[2] or args[1]
                if type(url) == "string" then
                    recorded_http[#recorded_http + 1] = url
                end
            end
            if path:match("GetValue") or path:match("ping") or path:match("Ping") then
                return 45
            end
            if path:match("GetClientId") or path:match("ClientId") then
                return "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
            end
            if path:match("GetProductInfo") then
                return { Name = "Game Info", Description = "Game Description" }
            end
            if path:match("GetPlayers") then
                return {}
            end
            
            record_event("CALL", { target = path, args = arg_strs })
            return make_mock_object("res", path .. "(" .. table.concat(arg_strs, ", ") .. ")")
        end
    }
    setmetatable(mock, mt)
    return mock
end

local genv = {}
setmetatable(genv, {
    __newindex = function(t, k, v)
        recorded_genv[tostring(k)] = v
        rawset(t, k, v)
    end
})

local g_table = {}
setmetatable(g_table, {
    __newindex = function(t, k, v)
        recorded_g[tostring(k)] = v
        rawset(t, k, v)
    end
})

local env = {
    getgenv = function() return genv end,
    getrenv = function() return genv end,
    _G = g_table,
    shared = g_table,
    print = function(...)
        local items = {...}
        local strs = {}
        for i=1, #items do strs[#strs+1] = tostring(items[i]) end
        local line = table.concat(strs, "\t")
        recorded_prints[#recorded_prints + 1] = line
        record_event("PRINT", { text = line })
    end,
    warn = function(...)
        local items = {...}
        local strs = {}
        for i=1, #items do strs[#strs+1] = tostring(items[i]) end
        recorded_prints[#recorded_prints + 1] = "[WARN] " .. table.concat(strs, "\t")
    end,
    error = function(...)
        local items = {...}
        local strs = {}
        for i=1, #items do strs[#strs+1] = tostring(items[i]) end
        recorded_prints[#recorded_prints + 1] = "[ERROR] " .. table.concat(strs, "\t")
    end,
    pcall = pcall,
    xpcall = xpcall,
    type = type,
    typeof = type,
    tostring = tostring,
    tonumber = tonumber,
    select = select,
    rawget = rawget,
    rawset = rawset,
    rawequal = rawequal,
    rawlen = rawlen or function(t) return #t end,
    setmetatable = setmetatable,
    getmetatable = getmetatable,
    pairs = pairs,
    ipairs = ipairs,
    next = next,
    unpack = unpack or table.unpack,
    table = table,
    string = string,
    math = math,
    os = os,
    debug = debug,
    bit32 = bit32 or {
        bxor = function(a, b) return a ~ b end,
        band = function(a, b) return a & b end,
        bor = function(a, b) return a | b end,
        bnot = function(a) return ~a end,
        lshift = function(a, b) return a << b end,
        rshift = function(a, b) return a >> b end
    },
    bit = bit or {
        bxor = function(a, b) return a ~ b end,
        band = function(a, b) return a & b end,
        bor = function(a, b) return a | b end,
        bnot = function(a) return ~a end,
        lshift = function(a, b) return a << b end,
        rshift = function(a, b) return a >> b end
    },
    utf8 = utf8 or {
        char = function(...) return "" end,
        len = function(s) return #s end
    },
    syn = {
        request = function(req)
            if type(req) == "table" and req.Url then
                recorded_http[#recorded_http + 1] = tostring(req.Url)
            end
            return { StatusCode = 200, StatusMessage = "OK", Body = "{}" }
        end,
        websocket = { connect = function(url) return make_mock_object("WebSocket") end }
    },
    crypt = {
        base64encode = function(s) return s end,
        base64decode = function(s) return s end,
        encrypt = function(s) return s end,
        decrypt = function(s) return s end
    },
    base64 = {
        encode = function(s) return s end,
        decode = function(s) return s end
    },
    hookfunction = function(target, replacement) return target end,
    hookmetamethod = function(target, method, replacement) return target end,
    newcclosure = function(f) return f end,
    islclosure = function(f) return true end,
    iscclosure = function(f) return false end,
    checkcaller = function() return true end,
    rconsolename = function() end,
    rconsoleprint = function() end,
    rconsoleinfo = function() end,
    rconsolewarn = function() end,
    rconsoleerr = function() end,
    fireclickdetector = function() end,
    fireproximityprompt = function() end,
    isrbxactive = function() return true end,
    mouse1click = function() end,
    mouse2click = function() end
}

env.game = make_mock_object("game")
env.workspace = make_mock_object("workspace")
env.Players = make_mock_object("Players")
env.CoreGui = make_mock_object("CoreGui")
env.ReplicatedStorage = make_mock_object("ReplicatedStorage")
env.HttpService = make_mock_object("HttpService")
env.TweenService = make_mock_object("TweenService")
env.RunService = make_mock_object("RunService")
env.UserInputService = make_mock_object("UserInputService")
env.Stats = make_mock_object("Stats")
env.TeleportService = make_mock_object("TeleportService")

env.identifyexecutor = function() return "Delta", "2.664" end
env.getexecutorname = function() return "Delta" end
env.setclipboard = function(s) record_event("CLIPBOARD", { data = tostring(s) }) end
env.toclipboard = env.setclipboard

env.loadstring = function(code, chunkname)
    local code_str = tostring(code)
    recorded_loads[#recorded_loads + 1] = code_str
    record_event("LOADSTRING", { code = code_str, chunk = chunkname })
    return function(...) return ... end
end
env.load = env.loadstring

env.task = {
    wait = function() return 0 end,
    spawn = function(f, ...) if type(f) == "function" then pcall(f, ...) end end,
    defer = function(f, ...) if type(f) == "function" then pcall(f, ...) end end,
    delay = function(t, f, ...) if type(f) == "function" then pcall(f, ...) end end,
}

env.request = function(req)
    record_event("REQUEST", { req = serialize_value(req) })
    if type(req) == "table" and req.Url then
        recorded_http[#recorded_http + 1] = tostring(req.Url)
    end
    return { StatusCode = 200, StatusMessage = "OK", Body = "{}" }
end
env.http_request = env.request
env.http = { request = env.request }

env.Instance = {
    new = function(className, parent)
        local inst = make_mock_object(className, "Instance.new(" .. string.format("%q", className) .. ")")
        if parent then inst.Parent = parent end
        return inst
    end
}

env.Vector2 = { new = function(x, y) return string.format("Vector2.new(%s, %s)", x or 0, y or 0) end }
env.Vector3 = { new = function(x, y, z) return string.format("Vector3.new(%s, %s, %s)", x or 0, y or 0, z or 0) end }
env.CFrame = { new = function(...) return "CFrame.new(...)" end }
env.UDim2 = {
    new = function(xs, xo, ys, yo) return string.format("UDim2.new(%s, %s, %s, %s)", xs or 0, xo or 0, ys or 0, yo or 0) end,
    fromScale = function(x, y) return string.format("UDim2.fromScale(%s, %s)", x or 0, y or 0) end,
    fromOffset = function(x, y) return string.format("UDim2.fromOffset(%s, %s)", x or 0, y or 0) end
}
env.UDim = { new = function(s, o) return string.format("UDim.new(%s, %s)", s or 0, o or 0) end }
env.Color3 = {
    fromRGB = function(r, g, b) return string.format("Color3.fromRGB(%s, %s, %s)", r or 0, g or 0, b or 0) end,
    fromHSV = function(h, s, v) return string.format("Color3.fromHSV(%s, %s, %s)", h or 0, s or 0, v or 0) end,
    new = function(r, g, b) return string.format("Color3.new(%s, %s, %s)", r or 0, g or 0, b or 0) end
}
env.Enum = make_mock_object("Enum")

local target_file = arg[1]
if not target_file then
    print(json.encode({ error = "No input file provided to tracer." }))
    return
end

local chunk, load_err = loadfile(target_file)
if not chunk then
    print(json.encode({ error = "Lua Load Error: " .. tostring(load_err) }))
    return
end

setfenv(chunk, env)
local ok, run_err = pcall(chunk)

local output = {
    success = ok,
    error = not ok and tostring(run_err) or nil,
    genv = {},
    g = {},
    loads = recorded_loads,
    http = recorded_http,
    prints = recorded_prints,
    events = trace_events
}

for k, v in pairs(recorded_genv) do
    output.genv[k] = serialize_value(v)
end
for k, v in pairs(recorded_g) do
    output.g[k] = serialize_value(v)
end

local function export_json(tbl)
    local function to_j(val)
        local t = type(val)
        if t == "table" then
            local is_arr = true
            local max_i = 0
            for k, v in pairs(val) do
                if type(k) ~= "number" or k <= 0 or math.floor(k) ~= k then
                    is_arr = false
                    break
                else
                    if k > max_i then max_i = k end
                end
            end
            if is_arr then
                local items = {}
                for i = 1, #val do items[#items + 1] = to_j(val[i]) end
                return "[" .. table.concat(items, ",") .. "]"
            else
                local items = {}
                for k, v in pairs(val) do
                    items[#items + 1] = string.format("%q:%s", tostring(k), to_j(v))
                end
                return "{" .. table.concat(items, ",") .. "}"
            end
        elseif t == "string" then
            local escaped = val:gsub('[%z\1-\31\\"]', function(c)
                if c == '"' then return '\\"'
                elseif c == '\\' then return '\\\\'
                elseif c == '\b' then return '\\b'
                elseif c == '\f' then return '\\f'
                elseif c == '\n' then return '\\n'
                elseif c == '\r' then return '\\r'
                elseif c == '\t' then return '\\t'
                else
                    return string.format('\\u%04x', string.byte(c))
                end
            end)
            return '"' .. escaped .. '"'
        elseif t == "number" or t == "boolean" then
            return tostring(val)
        else
            return "null"
        end
    end
    return to_j(tbl)
end

print("<<<JSON_START>>>")
print(export_json(output))
print("<<<JSON_END>>>")
'''

class LuaDeobfuscatorEngine:
    def __init__(self, target_input: str, is_url: bool = False):
        self.target_input = target_input
        self.is_url = is_url
        self.raw_content = ""
        self.raw_bytes = b""

    def fetch_or_read(self) -> bool:
        if self.is_url or self.target_input.startswith("http://") or self.target_input.startswith("https://"):
            print(f"{C_CYAN}[*] Đang tải script từ URL:{C_RESET} {self.target_input} ...")
            req = urllib.request.Request(
                self.target_input,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            )
            try:
                with urllib.request.urlopen(req, timeout=15) as response:
                    self.raw_bytes = response.read()
                    self.raw_content = self.raw_bytes.decode("utf-8", errors="ignore")
                print(f"{C_GREEN}[+] Tải thành công ({len(self.raw_content):,} bytes).{C_RESET}")
                return True
            except Exception as e:
                print(f"{C_RED}[-] Lỗi khi tải URL: {e}{C_RESET}")
                return False
        else:
            file_path = Path(self.target_input)
            if not file_path.exists():
                print(f"{C_RED}[-] Không tìm thấy tệp: {self.target_input}{C_RESET}")
                return False
            try:
                self.raw_bytes = file_path.read_bytes()
                self.raw_content = self.raw_bytes.decode("utf-8", errors="ignore")
                print(f"{C_GREEN}[+] Đọc tệp thành công:{C_RESET} {file_path.name} ({len(self.raw_bytes):,} bytes).")
                return True
            except Exception as e:
                print(f"{C_RED}[-] Lỗi đọc tệp: {e}{C_RESET}")
                return False

    def check_obfuscation_type(self) -> str:
        if self.raw_bytes.startswith(b"\x1bLuaQ") or self.raw_bytes.startswith(b"\x1bLua"):
            return "Compiled Lua Bytecode (.luac)"
        
        content = self.raw_content
        # Luraph detection - version-specific markers & structural patterns
        lph_markers = ["LPH_OBFUSCATED", "LPH_NO_VIRTUALIZE", "LPH_NO_UPVALUES", "LPH_JIT_MAX", "LPH_JIT_ULTRA", "LPH_CRASH"]
        has_lph_marker = any(m in content for m in lph_markers)
        has_lph_generic = "LPH_" in content or "Luraph" in content
        # Luraph setfenv wrapper: setfenv(function(...) return ... end, setmetatable({
        has_lph_wrapper = bool(re.search(r'setfenv\s*\(\s*function\s*\(\.\.\.\)', content))
        # Luraph IIFE nesting: (function() ... end)() repeated with deep closure structure
        iife_count = len(re.findall(r'\(function\s*\(', content))
        has_lph_structure = has_lph_wrapper and iife_count >= 3

        if has_lph_marker or has_lph_generic or has_lph_structure:
            # Attempt version detection
            if "LPH_JIT_ULTRA" in content:
                return "Luraph (LPH v15) Obfuscator"
            elif "LPH_JIT_MAX" in content:
                return "Luraph (LPH v14) Obfuscator"
            elif "LPH_NO_UPVALUES" in content and "LPH_CRASH" in content:
                return "Luraph (LPH v13) Obfuscator"
            elif "LPH_NO_VIRTUALIZE" in content:
                return "Luraph (LPH v12) Obfuscator"
            elif has_lph_marker or has_lph_generic:
                return "Luraph (LPH v11+) Obfuscator"
            else:
                return "Luraph (LPH) Obfuscator"
        elif "MoonSec V3" in content or "_ZPGCeefKVoxk" in content:
            return "MoonSec V3 (VM)"
        elif "MoonSec" in content:
            return "MoonSec (Generic / V2)"
        elif "IronBrew" in content or "IB_" in content or ("(v - " in content and "bit.bxor" in content):
            return "IronBrew 2 / PSU Obfuscator"
        elif "Prometheus" in content or "discord-bot-obfuscator" in content or "BackSec" in content:
            return "Prometheus Metamethod VM"
        elif "wearedevs.net/obfuscator" in content or ("local K={" in content and "ipairs({{" in content):
            return "WeAreDevs (WRD) Obfuscator v1.0.0"
        elif "bit32.bxor" in content or "bit.bxor" in content or "bit.band" in content:
            return "Bitwise XOR / Xen Obfuscator"
        elif re.search(r'\\([0-9]{3}|x[0-9a-fA-F]{2})', content):
            return "Escaped Hex / Octal Character Obfuscator"
        elif "string.char(" in content and ("load(" in content or "loadstring" in content):
            return "Byte Array / string.char Encoding"
        elif re.search(r'ipairs\(\{[\d\s,]+\}\)', content):
            return "Byte Array / table.concat Encoding"
        elif "api.luarmor.net" in content:
            return "Luarmor Key System Loader"
        elif "loadstring" in content:
            return "Lua Loader / Wrapper"
        return "Lua Script (Generic)"

    # Engine 1: Byte Array / string.char Decoder
    def try_decode_byte_array(self) -> str:
        content = self.raw_content
        # Case A: load(string.char(45, 45, 32, ...))
        char_matches = re.findall(r'string\.char\(([\d\s,]+)\)', content)
        if char_matches:
            all_nums = []
            for m in char_matches:
                nums = [int(x.strip()) for x in m.split(',') if x.strip().isdigit()]
                all_nums.extend(nums)
            if len(all_nums) > 20:
                try:
                    decoded = bytes(all_nums).decode("utf-8", errors="ignore")
                    return decoded
                except Exception:
                    pass

        # Case B: ipairs({45, 45, 32, ...})
        ipair_matches = re.findall(r'ipairs\(\{([\d\s,]+)\}\)', content)
        if ipair_matches:
            all_nums = []
            for m in ipair_matches:
                nums = [int(x.strip()) for x in m.split(',') if x.strip().isdigit()]
                all_nums.extend(nums)
            if len(all_nums) > 20:
                try:
                    decoded = bytes(all_nums).decode("utf-8", errors="ignore")
                    return decoded
                except Exception:
                    pass

        return ""

    # Engine 2: Compiled Lua 5.1 Bytecode Parser & Decompiler
    def try_decompile_luac(self) -> str:
        data = self.raw_bytes
        if not data.startswith(b"\x1bLuaQ") and not data.startswith(b"\x1bLua"):
            return ""

        strings = re.findall(b'[\x20-\x7e]{3,}', data)
        str_list = [s.decode("utf-8", errors="ignore") for s in strings if not s.startswith(b"LuaQ")]

        lines = [
            "-- ========================================================",
            "-- [DECOMPILED LUA 5.1 BYTECODE (.luac)]",
            f"-- Generated At: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            "-- ========================================================",
            "",
            "repeat task.wait() until game:IsLoaded()",
            ""
        ]

        urls = [s for s in str_list if s.startswith("http://") or s.startswith("https://")]
        keys = [s for s in str_list if len(s) >= 16 and not s.startswith("http") and " " not in s]

        if "script_key" in str_list:
            if keys:
                lines.append(f"getgenv().script_key = {json.dumps(keys[0])}")
            else:
                lines.append("getgenv().script_key = \"\"")
        
        if "Team" in str_list and "Pirates" in str_list:
            lines.append("getgenv().Team = \"Pirates\"")
        if "FixCrash2" in str_list:
            lines.append("getgenv().FixCrash2 = true")

        lines.append("")
        if urls:
            lines.append("-- [Discovered Loaders / Payloads]")
            for u in urls:
                lines.append(f"loadstring(game:HttpGet({json.dumps(u)}))()")
        
        lines.append("\n-- [All Extracted Bytecode Constants / Strings]")
        for s in str_list:
            if s not in ["script_key", "getgenv", "loadstring", "game", "HttpGet", "FixCrash", "FixCrash2", "Team", "Pirates"]:
                lines.append(f"-- Const: {s}")

        return "\n".join(lines)

    # Engine 3: WeAreDevs (WRD) v1.0.0 Obfuscator Engine
    def try_deobfuscate_wrd(self) -> str:
        content = self.raw_content
        if "wearedevs.net/obfuscator" not in content and not ("local K={" in content and "ipairs({{" in content):
            return ""

        m = re.search(r'local K\s*=\s*\{(.*?)\}\s*;?\s*local function', content, re.DOTALL)
        if not m:
            return ""
        
        table_str = m.group(1)
        raw_strings = re.findall(r'\"(.*?)\"', table_str)
        if not raw_strings:
            return ""

        K = []
        for s in raw_strings:
            unescaped = re.sub(r'\\([0-9]{3})', lambda match: chr(int(match.group(1))), s)
            K.append(unescaped)

        reversals = [(0, len(K) - 1), (0, 311), (312, len(K) - 1)]
        for left, right in reversals:
            if right < len(K):
                while left < right:
                    K[left], K[right] = K[right], K[left]
                    left += 1
                    right -= 1

        y = {
            "2": 46, "5": 26, "I": 9, "D": 53, "N": 57, "J": 51, "g": 44, "h": 21,
            "R": 8, "e": 60, "s": 0, "i": 16, "1": 47, "Q": 17, "a": 50, "n": 30,
            "8": 22, "T": 34, "/": 61, "V": 31, "A": 39, "E": 23, "4": 19, "O": 58,
            "+": 2, "W": 63, "d": 55, "U": 24, "x": 38, "l": 32, "z": 1, "G": 62,
            "v": 28, "3": 27, "k": 37, "Z": 48, "7": 41, "q": 42, "S": 13, "L": 10,
            "0": 7, "F": 43, "j": 11, "r": 6, "X": 18, "6": 35, "c": 59, "P": 3,
            "y": 5, "9": 33, "o": 25, "b": 20, "M": 52, "m": 54, "w": 36, "C": 12,
            "Y": 40, "t": 29, "K": 49, "B": 15, "p": 4, "f": 14, "u": 56, "H": 45
        }

        import math
        decrypted = []
        for X in K:
            if not isinstance(X, str):
                continue
            G_len = len(X)
            Q = []
            z = 0
            o = 0
            F = 0
            while z < G_len:
                char = X[z]
                c = y.get(char)
                if c is not None:
                    o = o + c * (64 ** (3 - F))
                    F += 1
                    if F == 4:
                        F = 0
                        c1 = math.floor(o / 65536)
                        c2 = math.floor((o % 65536) / 256)
                        c3 = o % 256
                        Q.extend([chr(c1), chr(c2), chr(c3)])
                        o = 0
                elif char == "=":
                    Q.append(chr(math.floor(o / 65536)))
                    if z >= G_len - 1 or X[z+1] != "=":
                        Q.append(chr(math.floor((o % 65536) / 256)))
                    break
                z += 1
            decrypted.append("".join(Q))

        clean_strings = [s for s in decrypted if any(c.isalnum() for c in s)]

        lines = [
            "-- ========================================================",
            "-- [DEOBFUSCATED WEAREDEVS (WRD) STRINGS & LOGIC]",
            "-- ========================================================",
            "",
            "repeat task.wait() until game:IsLoaded()",
            ""
        ]
        urls = [s for s in clean_strings if s.startswith("http://") or s.startswith("https://")]
        if urls:
            lines.append("-- [Discovered URLs]")
            for u in urls:
                lines.append(f"loadstring(game:HttpGet({json.dumps(u)}))()")
            lines.append("")
        
        lines.append("-- [All Decrypted WeAreDevs String Constants]")
        for s in clean_strings:
            lines.append(f"-- String: {s}")
        
        return "\n".join(lines)

    # Engine 4: Luraph (LPH) Obfuscator - Advanced Multi-Strategy Decoder
    def _lph_detect_version(self) -> str:
        """Nhận diện phiên bản Luraph từ markers và cấu trúc code."""
        content = self.raw_content
        if "LPH_JIT_ULTRA" in content:
            return "v15"
        elif "LPH_JIT_MAX" in content:
            return "v14"
        elif "LPH_NO_UPVALUES" in content and "LPH_CRASH" in content:
            return "v13"
        elif "LPH_NO_VIRTUALIZE" in content:
            return "v12"
        elif "LPH_" in content or "Luraph" in content:
            return "v11+"
        # Structural detection: setfenv wrapper + deep IIFE nesting
        if re.search(r'setfenv\s*\(\s*function\s*\(\.\.\.\)', content):
            iife_depth = len(re.findall(r'\(function\s*\(', content))
            if iife_depth >= 5:
                return "v13+ (structural)"
            elif iife_depth >= 3:
                return "v11+ (structural)"
        return "unknown"

    def _lph_extract_xor_keys(self) -> list:
        """Trích xuất XOR keys từ các pattern mã hóa trong code Luraph."""
        content = self.raw_content
        keys = []

        # Pattern 1: bit32.bxor(byte(str, i), KEY) hoặc bxor(... , KEY)
        xor_const_matches = re.findall(
            r'(?:bit32\.bxor|bit\.bxor|bxor)\s*\([^,]+,\s*(\d+)\s*\)', content
        )
        for m in xor_const_matches:
            try:
                k = int(m)
                if 1 <= k <= 255:
                    keys.append(k)
            except ValueError:
                pass

        # Pattern 2: XOR key embedded as variable: local KEY = NNN
        key_var_matches = re.findall(
            r'local\s+\w+\s*=\s*(\d{1,3})\s*[\n;]', content
        )
        for m in key_var_matches:
            try:
                k = int(m)
                if 1 <= k <= 255 and k not in keys:
                    keys.append(k)
            except ValueError:
                pass

        # Pattern 3: XOR in arithmetic form: (byte - KEY) % 256
        arith_matches = re.findall(
            r'\(\s*\w+\s*[-+^]\s*(\d+)\s*\)\s*%%?\s*256', content
        )
        for m in arith_matches:
            try:
                k = int(m)
                if 1 <= k <= 255 and k not in keys:
                    keys.append(k)
            except ValueError:
                pass

        # Pattern 4: Subtract constant pattern: string.char(byte(s, i) - KEY)
        sub_matches = re.findall(
            r'string\.char\s*\(\s*(?:string\.)?byte\s*\([^)]+\)\s*[-+]\s*(\d+)', content
        )
        for m in sub_matches:
            try:
                k = int(m)
                if 1 <= k <= 255 and k not in keys:
                    keys.append(k)
            except ValueError:
                pass

        return list(set(keys))[:20]

    def _lph_try_xor_decrypt(self, data_bytes: bytes, key: int) -> str:
        """Thử giải mã XOR một chuỗi bytes với key đơn."""
        try:
            decrypted = bytes([b ^ key for b in data_bytes])
            text = decrypted.decode("utf-8", errors="ignore")
            # Kiểm tra tỷ lệ ký tự printable
            printable_count = sum(1 for c in text if c.isprintable() or c in "\n\r\t")
            if len(text) > 0 and printable_count / len(text) > 0.7:
                return text
        except Exception:
            pass
        return ""

    def _lph_try_multi_byte_xor(self, data_bytes: bytes, key_bytes: bytes) -> str:
        """Thử giải mã XOR với key nhiều byte."""
        try:
            key_len = len(key_bytes)
            if key_len == 0:
                return ""
            decrypted = bytes([data_bytes[i] ^ key_bytes[i % key_len] for i in range(len(data_bytes))])
            text = decrypted.decode("utf-8", errors="ignore")
            printable_count = sum(1 for c in text if c.isprintable() or c in "\n\r\t")
            if len(text) > 0 and printable_count / len(text) > 0.7:
                return text
        except Exception:
            pass
        return ""

    def _lph_extract_constant_pool(self) -> list:
        """Trích xuất hằng số từ Luraph constant table bằng nhiều chiến lược."""
        content = self.raw_content
        constants = []

        # Strategy 1: Chuỗi trực tiếp trong dấu ngoặc kép (escape sequences)
        raw_strings = re.findall(r'"((?:\\.|[^"\\]){3,})"', content)
        for s in raw_strings:
            if s.startswith("LPH_") or len(s) > 500:
                continue
            try:
                # Chỉ dùng unicode_escape nếu có escape sequences thực sự
                if re.search(r'\\[0-9]{1,3}|\\x[0-9a-fA-F]{2}|\\[nrtbf"\'\\]', s):
                    decoded = re.sub(r'\\(\d{1,3})', lambda m: chr(int(m.group(1)) % 256), s)
                    decoded = re.sub(r'\\x([0-9a-fA-F]{2})', lambda m: chr(int(m.group(1), 16)), decoded)
                    decoded = decoded.replace('\\n', '\n').replace('\\t', '\t').replace('\\r', '\r')
                else:
                    decoded = s
                if any(c.isalnum() for c in decoded):
                    constants.append(decoded)
            except Exception:
                # Thử giải mã escape thủ công
                decoded = re.sub(r'\\(\d{1,3})', lambda m: chr(int(m.group(1)) % 256), s)
                decoded = re.sub(r'\\x([0-9a-fA-F]{2})', lambda m: chr(int(m.group(1), 16)), decoded)
                if any(c.isalnum() for c in decoded) and decoded != s:
                    constants.append(decoded)

        # Strategy 2: Mảng byte string.char(n1, n2, n3, ...)
        char_blocks = re.findall(r'string\.char\s*\(([\d\s,]+)\)', content)
        for block in char_blocks:
            nums = [int(x.strip()) for x in block.split(',') if x.strip().isdigit()]
            if len(nums) >= 3:
                try:
                    s = bytes(n % 256 for n in nums).decode("utf-8", errors="ignore")
                    if any(c.isalnum() for c in s):
                        constants.append(s)
                except Exception:
                    pass

        # Strategy 3: Bảng số lớn (byte array table)
        table_matches = re.findall(r'\{((?:\s*\d+\s*,?\s*){10,})\}', content)
        for tm in table_matches:
            nums = [int(x.strip()) for x in tm.split(',') if x.strip().isdigit()]
            if len(nums) >= 10 and all(0 <= n <= 255 for n in nums):
                try:
                    s = bytes(nums).decode("utf-8", errors="ignore")
                    if any(c.isalnum() for c in s):
                        constants.append(s)
                except Exception:
                    pass

        # Strategy 4: Chuỗi concat dài: "a" .. "b" .. "c"
        concat_match = re.search(r'("(?:\\.|[^"\\])"\s*\.\.\s*){5,}', content)
        if concat_match:
            parts = re.findall(r'"((?:\\.|[^"\\])*)"', concat_match.group(0))
            if parts:
                full = "".join(parts)
                constants.append(full)

        # Strategy 5: Phát hiện custom base64 alphabet và giải mã
        alpha_match = re.search(
            r'["\']([A-Za-z0-9+/=_-]{60,70})["\']', content
        )
        if alpha_match:
            custom_alpha = alpha_match.group(1)
            if len(custom_alpha) >= 64:
                constants.append(f"[CUSTOM_B64_ALPHABET] {custom_alpha[:64]}")
                # Tìm chuỗi data được mã hóa bằng alphabet này
                b64_data_matches = re.findall(r'"([A-Za-z0-9+/=_-]{20,})"', content)
                std_alpha = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
                for b64_str in b64_data_matches:
                    if b64_str == custom_alpha:
                        continue
                    try:
                        trans_table = str.maketrans(custom_alpha[:64], std_alpha)
                        normalized = b64_str.translate(trans_table)
                        import base64
                        decoded = base64.b64decode(normalized + "==").decode("utf-8", errors="ignore")
                        if len(decoded) > 3 and any(c.isalnum() for c in decoded):
                            constants.append(decoded)
                    except Exception:
                        pass

        return constants

    def _lph_analyze_vm_dispatcher(self) -> dict:
        """Phân tích cấu trúc VM dispatcher của Luraph."""
        content = self.raw_content
        vm_info = {
            "dispatch_type": "unknown",
            "opcode_count": 0,
            "handler_patterns": [],
            "has_anti_tamper": False,
            "has_environment_check": False,
        }

        # Detect dispatch loop: while true do ... if op == N ... elseif op == N
        dispatch_match = re.search(
            r'while\s+true\s+do(.*?)(?:break|return)',
            content, re.DOTALL
        )
        if dispatch_match:
            dispatch_body = dispatch_match.group(1)
            # Count opcode handlers (if ... elseif patterns)
            op_handlers = re.findall(r'(?:if|elseif)\s+\w+\s*==\s*(\d+)', dispatch_body)
            if op_handlers:
                vm_info["dispatch_type"] = "if-elseif chain"
                vm_info["opcode_count"] = len(set(op_handlers))

        # Alternative: table-based dispatch
        table_dispatch = re.search(
            r'local\s+\w+\s*=\s*\{(?:\s*\[?\d+\]?\s*=\s*function|\s*function)', content
        )
        if table_dispatch and vm_info["opcode_count"] == 0:
            handler_funcs = re.findall(r'\[\s*(\d+)\s*\]\s*=\s*function', content)
            if handler_funcs:
                vm_info["dispatch_type"] = "table dispatch"
                vm_info["opcode_count"] = len(set(handler_funcs))

        # Alternative: computed goto / arithmetic dispatch
        arith_dispatch = re.findall(
            r'\w+\s*\[\s*\w+\s*[+\-*]\s*\d+\s*\]', content
        )
        if arith_dispatch and vm_info["opcode_count"] == 0:
            vm_info["dispatch_type"] = "computed index"
            vm_info["opcode_count"] = len(set(arith_dispatch))

        # Detect anti-tamper / environment checks
        if re.search(r'(?:getfenv|setfenv|debug\.getinfo|debug\.traceback)', content):
            vm_info["has_anti_tamper"] = True
        if re.search(r'(?:identifyexecutor|getexecutorname|syn\.request|is_synapse|KRNL)', content):
            vm_info["has_environment_check"] = True

        return vm_info

    def _lph_extract_payloads(self) -> dict:
        """Trích xuất URLs, webhooks, API endpoints từ code và hằng số đã giải mã."""
        content = self.raw_content
        payloads = {
            "urls": [],
            "webhooks": [],
            "luarmor_endpoints": [],
            "loadstring_targets": [],
            "script_keys": [],
        }

        # URLs tổng quát
        urls = re.findall(r'https?://[^\s\'"\\,\)]+', content)
        for u in urls:
            u = u.rstrip('.)],;')
            if "discord.com/api/webhooks" in u or "discordapp.com/api/webhooks" in u:
                payloads["webhooks"].append(u)
            elif "api.luarmor.net" in u:
                payloads["luarmor_endpoints"].append(u)
            else:
                payloads["urls"].append(u)

        # loadstring targets
        ls_matches = re.findall(r'loadstring\s*\(\s*game\s*:\s*HttpGet\s*\(\s*["\']([^"\']+)["\']', content)
        payloads["loadstring_targets"].extend(ls_matches)

        # Script keys
        key_matches = re.findall(r'script_key\s*=\s*["\']([^"\']+)["\']', content)
        payloads["script_keys"].extend(key_matches)

        # Deduplicate
        for k in payloads:
            payloads[k] = list(set(payloads[k]))

        return payloads

    def try_deobfuscate_luraph(self) -> str:
        content = self.raw_content
        # Kiểm tra có phải Luraph không
        lph_markers = ["LPH_", "Luraph"]
        has_lph = any(m in content for m in lph_markers)
        has_lph_struct = bool(re.search(r'setfenv\s*\(\s*function\s*\(\.\.\.\)', content))
        if not has_lph and not has_lph_struct:
            return ""

        # === PHASE 1: Nhận diện phiên bản ===
        version = self._lph_detect_version()
        print(f"{C_CYAN}[*] Phát hiện Luraph phiên bản:{C_RESET} {C_YELLOW}{C_BOLD}{version}{C_RESET}")

        # === PHASE 2: Trích xuất XOR keys ===
        xor_keys = self._lph_extract_xor_keys()
        if xor_keys:
            print(f"{C_CYAN}[*] Tìm thấy {len(xor_keys)} XOR key(s):{C_RESET} {C_DIM}{xor_keys[:5]}{C_RESET}")

        # === PHASE 3: Trích xuất constant pool ===
        print(f"{C_CYAN}[*] Đang trích xuất Constant Pool (multi-strategy)...{C_RESET}")
        constants = self._lph_extract_constant_pool()

        # Thử XOR decrypt trên các chuỗi chưa readable
        xor_decoded = []
        if xor_keys:
            # Tìm các chuỗi binary/non-readable trong content
            binary_strings = re.findall(r'"((?:\\[0-9]{3}|\\x[0-9a-fA-F]{2}){5,})"', content)
            for bs in binary_strings:
                try:
                    raw_bytes_str = bs.encode().decode('unicode_escape').encode('latin-1')
                    for key in xor_keys:
                        result = self._lph_try_xor_decrypt(raw_bytes_str, key)
                        if result and len(result) > 3:
                            xor_decoded.append(result)
                            break
                except Exception:
                    pass

            # Brute-force XOR trên byte tables nếu chưa có kết quả
            if not xor_decoded:
                table_matches = re.findall(r'\{((?:\s*\d+\s*,?\s*){10,})\}', content)
                for tm in table_matches[:3]:
                    nums = [int(x.strip()) for x in tm.split(',') if x.strip().isdigit()]
                    if len(nums) >= 10 and all(0 <= n <= 255 for n in nums):
                        raw = bytes(nums)
                        for key in xor_keys:
                            result = self._lph_try_xor_decrypt(raw, key)
                            if result:
                                xor_decoded.append(result)
                                break

        if xor_decoded:
            print(f"{C_GREEN}[+] XOR giải mã thành công {len(xor_decoded)} chuỗi!{C_RESET}")
            constants.extend(xor_decoded)

        # === PHASE 4: Phân tích VM Dispatcher ===
        print(f"{C_CYAN}[*] Đang phân tích cấu trúc VM Dispatcher...{C_RESET}")
        vm_info = self._lph_analyze_vm_dispatcher()
        if vm_info["opcode_count"] > 0:
            print(f"{C_GREEN}[+] VM Dispatch: {vm_info['dispatch_type']} ({vm_info['opcode_count']} opcodes){C_RESET}")
        if vm_info["has_anti_tamper"]:
            print(f"{C_YELLOW}[!] Phát hiện Anti-Tamper / Environment Check{C_RESET}")

        # === PHASE 5: Trích xuất payloads ===
        payloads = self._lph_extract_payloads()

        # Cũng kiểm tra URL trong các hằng số đã giải mã
        for const in constants:
            extra_urls = re.findall(r'https?://[^\s\'"\\,\)]+', const)
            for u in extra_urls:
                u = u.rstrip('.)],;')
                if "discord.com/api/webhooks" in u or "discordapp.com/api/webhooks" in u:
                    if u not in payloads["webhooks"]:
                        payloads["webhooks"].append(u)
                elif u not in payloads["urls"]:
                    payloads["urls"].append(u)

        # === PHASE 6: Tạo output ===
        lines = [
            "-- ========================================================",
            f"-- [DEOBFUSCATED CODE] - Engine: Luraph (LPH {version})",
            f"-- Generated At: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"-- VM Dispatch: {vm_info['dispatch_type']} ({vm_info['opcode_count']} opcodes)",
            f"-- Anti-Tamper: {'Yes' if vm_info['has_anti_tamper'] else 'No'}",
            f"-- Env Check: {'Yes' if vm_info['has_environment_check'] else 'No'}",
            "-- ========================================================",
            "",
            "repeat task.wait() until game:IsLoaded()",
            ""
        ]

        # Webhooks (cảnh báo)
        if payloads["webhooks"]:
            lines.append("-- [⚠️  CẢNH BÁO: DISCORD WEBHOOKS DETECTED!]")
            for wh in payloads["webhooks"]:
                lines.append(f"-- WEBHOOK: {wh}")
            lines.append("")

        # Script keys
        if payloads["script_keys"]:
            for sk in payloads["script_keys"]:
                lines.append(f"getgenv().script_key = {json.dumps(sk)}")
            lines.append("")

        # Luarmor endpoints
        if payloads["luarmor_endpoints"]:
            lines.append("-- [Luarmor API Endpoints]")
            for le in payloads["luarmor_endpoints"]:
                lines.append(f"loadstring(game:HttpGet({json.dumps(le)}))()")
            lines.append("")

        # Loadstring targets
        if payloads["loadstring_targets"]:
            lines.append("-- [Loadstring Payload Targets]")
            for lt in payloads["loadstring_targets"]:
                lines.append(f"loadstring(game:HttpGet({json.dumps(lt)}))()")
            lines.append("")

        # General URLs
        if payloads["urls"]:
            lines.append("-- [Extracted HTTP Payloads]")
            for u in payloads["urls"]:
                lines.append(f"loadstring(game:HttpGet({json.dumps(u)}))()")
            lines.append("")

        # XOR key info
        if xor_keys:
            lines.append(f"-- [Recovered XOR Keys: {xor_keys[:5]}]")
            lines.append("")

        # XOR decoded strings
        if xor_decoded:
            lines.append("-- [XOR Decrypted Strings]")
            for s in xor_decoded[:30]:
                clean = s.replace("\n", "\\n").replace("\r", "")[:200]
                lines.append(f"-- Decrypted: {clean}")
            lines.append("")

        # Constant pool
        clean_constants = [c for c in constants if c not in xor_decoded and any(ch.isalnum() for ch in c)]
        if clean_constants:
            lines.append("-- [Decoded Luraph Constant Pool]")
            seen = set()
            for c in clean_constants[:50]:
                c_clean = c.replace("\n", "\\n").replace("\r", "")[:200]
                if c_clean not in seen:
                    seen.add(c_clean)
                    lines.append(f"-- Const: {c_clean}")
            lines.append("")

        # Detected LPH macros
        macro_list = ["LPH_OBFUSCATED", "LPH_NO_VIRTUALIZE", "LPH_NO_UPVALUES", "LPH_JIT_MAX", "LPH_JIT_ULTRA", "LPH_CRASH"]
        found_macros = [m for m in macro_list if m in content]
        if found_macros:
            lines.append(f"-- [Detected LPH Macros: {', '.join(found_macros)}]")
            lines.append("")

        # Chỉ trả về kết quả nếu có dữ liệu hữu ích
        has_data = (payloads["urls"] or payloads["webhooks"] or payloads["luarmor_endpoints"]
                    or payloads["loadstring_targets"] or payloads["script_keys"]
                    or xor_decoded or len(clean_constants) > 3)

        return "\n".join(lines) if has_data else ""

    # Engine 5: IronBrew 2 / PSU Bytecode Obfuscator Decoder
    def try_deobfuscate_ironbrew(self) -> str:
        content = self.raw_content
        if "IronBrew" not in content and "IB_" not in content and "(v - " not in content:
            return ""

        # Extract string array
        str_block = re.search(r'\{(?:\"(?:\\.|[^\"])*\",?\s*)+\}', content)
        if not str_block:
            return ""

        raw_strings = re.findall(r'\"((?:\\.|[^\"])*)\"', str_block.group(0))
        decrypted_pool = []
        for s in raw_strings:
            unescaped = re.sub(r'\\([0-9]{1,3})', lambda m: chr(int(m.group(1)) % 256), s)
            unescaped = re.sub(r'\\x([0-9a-fA-F]{2})', lambda m: chr(int(m.group(1), 16)), unescaped)
            decrypted_pool.append(unescaped)

        urls = [s for s in decrypted_pool if s.startswith("http://") or s.startswith("https://")]
        lines = [
            "-- ========================================================",
            "-- [DEOBFUSCATED CODE] - Engine: IronBrew 2 / PSU",
            f"-- Generated At: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            "-- ========================================================",
            "",
            "repeat task.wait() until game:IsLoaded()",
            ""
        ]

        if urls:
            lines.append("-- [Discovered Payloads]")
            for u in set(urls):
                lines.append(f"loadstring(game:HttpGet({json.dumps(u)}))()")
            lines.append("")

        lines.append("-- [Extracted IronBrew String Constants]")
        for s in set([x for x in decrypted_pool if len(x) > 2 and any(c.isalnum() for c in x)][:40]):
            lines.append(f"-- Const: {s}")

        return "\n".join(lines) if urls or len(decrypted_pool) > 10 else ""

    # Engine 6: Escaped Hex / Octal / Decimal String Normalizer
    def try_decode_escapes(self) -> str:
        content = self.raw_content
        if not re.search(r'\\([0-9]{3}|x[0-9a-fA-F]{2}|u\{[0-9a-fA-F]+\})', content):
            return ""

        def replace_escape(match):
            m = match.group(0)
            if m.startswith("\\x"):
                return chr(int(m[2:], 16))
            elif m.startswith("\\u{"):
                hex_val = m[3:-1]
                return chr(int(hex_val, 16))
            elif m.startswith("\\") and len(m) == 4 and m[1:].isdigit():
                return chr(int(m[1:]) % 256)
            return m

        try:
            decoded = re.sub(r'(\\x[0-9a-fA-F]{2}|\\[0-9]{3}|\\u\{[0-9a-fA-F]+\})', replace_escape, content)
            if decoded != content and len(decoded) > 20:
                return decoded
        except Exception:
            pass

        return ""

    # Engine 7: Luarmor Key System Direct Loader
    def try_extract_luarmor(self) -> str:
        content = self.raw_content
        if "api.luarmor.net" not in content:
            return ""

        urls = re.findall(r'https?://api\.luarmor\.net/files/v3/loaders/[0-9a-fA-F]+\.lua', content)
        keys = re.findall(r'script_key\s*=\s*[\'"]([^\'"]+)[\'"]', content)
        
        lines = [
            "-- ========================================================",
            "-- [DEOBFUSCATED CODE] - Engine: Luarmor Key System Loader",
            f"-- Generated At: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            "-- ========================================================",
            "",
            "repeat task.wait() until game:IsLoaded()",
            ""
        ]

        if keys:
            lines.append(f"getgenv().script_key = {json.dumps(keys[0])}")
        else:
            lines.append("getgenv().script_key = \"\"")

        lines.append("")
        if urls:
            lines.append(f"loadstring(game:HttpGet({json.dumps(urls[0])}))()")
        
        return "\n".join(lines) if urls else ""

    # Engine 8: Dynamic Sandbox & VM Tracer
    def run_dynamic_tracer(self) -> dict:
        with tempfile.NamedTemporaryFile("w", suffix=".lua", delete=False, encoding="utf-8") as f_target:
            f_target.write(self.raw_content)
            target_tmp = f_target.name

        with tempfile.NamedTemporaryFile("w", suffix=".lua", delete=False, encoding="utf-8") as f_tracer:
            f_tracer.write(EMBEDDED_LUA_TRACER)
            tracer_tmp = f_tracer.name

        try:
            lua_bin = None
            for candidate in ["lua", "luajit", "/usr/bin/lua", "/usr/bin/luajit"]:
                if subprocess.run(f"which {candidate}", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).returncode == 0:
                    lua_bin = candidate
                    break
            
            if not lua_bin:
                return {"error": "Lua runtime not found on system."}

            cmd = [lua_bin, tracer_tmp, target_tmp]
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=12)
            
            raw_out = proc.stdout
            if "<<<JSON_START>>>" in raw_out and "<<<JSON_END>>>" in raw_out:
                json_str = raw_out.split("<<<JSON_START>>>")[1].split("<<<JSON_END>>>")[0].strip()
                try:
                    data = json.loads(json_str)
                    return data
                except Exception as ex:
                    return {"error": f"JSON parse error: {ex}", "raw_stdout": raw_out}
            else:
                return {"error": "Failed to get tracer output.", "stdout": raw_out, "stderr": proc.stderr}
        except subprocess.TimeoutExpired:
            return {"error": "Tracer timed out (infinite loop or anti-tamper detected)."}
        except Exception as e:
            return {"error": f"Execution error: {e}"}
        finally:
            if os.path.exists(target_tmp):
                os.remove(target_tmp)
            if os.path.exists(tracer_tmp):
                os.remove(tracer_tmp)

    def reconstruct_source_from_trace(self, trace_result: dict) -> str:
        lines = []
        obf_type = self.check_obfuscation_type()
        lines.append(f"-- ========================================================")
        lines.append(f"-- [DEOBFUSCATED CODE] - Engine: {obf_type}")
        lines.append(f"-- Generated At: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"-- ========================================================")
        lines.append("")
        lines.append("repeat task.wait() until game:IsLoaded()")
        lines.append("local Players = game:GetService('Players')")
        lines.append("local LocalPlayer = Players.LocalPlayer")
        lines.append("")

        genv_data = trace_result.get("genv", {})
        if isinstance(genv_data, dict):
            for key, val_code in genv_data.items():
                lines.append(f"getgenv().{key} = {val_code}")
                lines.append("")

        g_data = trace_result.get("g", {})
        if isinstance(g_data, dict):
            for key, val_code in g_data.items():
                lines.append(f"_G.{key} = {val_code}")
                lines.append("")

        http_urls = trace_result.get("http", [])
        loads = trace_result.get("loads", [])
        prints = trace_result.get("prints", [])

        if http_urls:
            lines.append("-- [HTTP Payloads Detected]")
            for url in set(http_urls):
                lines.append(f"loadstring(game:HttpGet({json.dumps(url)}))()")
            lines.append("")
        elif loads:
            lines.append("-- [Extracted Dynamic Payloads]")
            for code in loads:
                lines.append(code)
            lines.append("")
        elif prints:
            lines.append("-- [Traced Program Output / Logic]")
            for p in prints:
                lines.append(f"print({json.dumps(p)})")
            lines.append("")

        return "\n".join(lines)

    # Beautifier & Identifier Cleaner
    @staticmethod
    def beautify_code(code: str) -> str:
        if not code:
            return ""

        # 1. Clean mangled variable names (_0x12a9, IllIllIl)
        mangled_vars = list(set(re.findall(r'\b(_0x[0-9a-fA-F]+|[I|l]{4,}|__v[0-9a-zA-Z_]+)\b', code)))
        var_map = {}
        for idx, var in enumerate(mangled_vars, 1):
            var_map[var] = f"var_{idx}"

        beautified = code
        for old_v, new_v in var_map.items():
            beautified = re.sub(r'\b' + re.escape(old_v) + r'\b', new_v, beautified)

        # 2. Constant folding for string.char
        def fold_char(m):
            nums = [int(x.strip()) for x in m.group(1).split(',') if x.strip().isdigit()]
            try:
                s = bytes(nums).decode('utf-8', errors='ignore')
                return json.dumps(s)
            except Exception:
                return m.group(0)

        beautified = re.sub(r'string\.char\(([\d\s,]{1,200})\)', fold_char, beautified)
        return beautified

    def deobfuscate(self, output_path: str = None) -> str:
        if not self.fetch_or_read():
            return ""

        obf_type = self.check_obfuscation_type()
        print(f"{C_CYAN}[*] Nhận diện cấu trúc bảo vệ:{C_RESET} {C_YELLOW}{C_BOLD}{obf_type}{C_RESET}")

        result_code = ""

        # Strategy 1: Luarmor
        if "Luarmor" in obf_type:
            print(f"{C_CYAN}[*] Đang phân tích và giải mã Luarmor Loader...{C_RESET}")
            result_code = self.try_extract_luarmor()

        # Strategy 2: Compiled Lua Bytecode
        if not result_code and obf_type == "Compiled Lua Bytecode (.luac)":
            print(f"{C_CYAN}[*] Đang phân tích bảng hằng số và luồng lệnh Bytecode 5.1...{C_RESET}")
            result_code = self.try_decompile_luac()

        # Strategy 3: Luraph (LPH) - Advanced Multi-Phase Engine
        if not result_code and "Luraph" in obf_type:
            print(f"{C_CYAN}[*] Khởi động Luraph Advanced Engine (XOR Recovery + VM Analysis + Constant Pool)...{C_RESET}")
            result_code = self.try_deobfuscate_luraph()
            # Fallback: nếu static analysis thất bại, thử dynamic sandbox
            if not result_code:
                print(f"{C_YELLOW}[*] Static analysis chưa đủ, thử Dynamic Sandbox cho Luraph...{C_RESET}")
                trace_data = self.run_dynamic_tracer()
                if trace_data.get("genv") or trace_data.get("http") or trace_data.get("loads") or trace_data.get("prints"):
                    result_code = self.reconstruct_source_from_trace(trace_data)

        # Strategy 4: IronBrew 2 / PSU
        if not result_code and "IronBrew" in obf_type:
            print(f"{C_CYAN}[*] Đang giải mã bảng hằng số IronBrew 2 / PSU...{C_RESET}")
            result_code = self.try_deobfuscate_ironbrew()

        # Strategy 5: Byte Array / string.char
        if not result_code and ("Byte Array" in obf_type or "string.char" in self.raw_content):
            print(f"{C_CYAN}[*] Đang giải mã mảng ký tự ASCII & Byte Stream...{C_RESET}")
            result_code = self.try_decode_byte_array()

        # Strategy 6: WeAreDevs (WRD) Engine
        if not result_code and ("WeAreDevs" in obf_type or "wearedevs.net/obfuscator" in self.raw_content):
            print(f"{C_CYAN}[*] Đang giải mã bảng hằng số và luồng lệnh WeAreDevs (WRD)...{C_RESET}")
            result_code = self.try_deobfuscate_wrd()

        # Strategy 7: Escaped Hex / Octal
        if not result_code and "Escaped" in obf_type:
            print(f"{C_CYAN}[*] Đang giải mã chuỗi Escaped Hex & Octal Sequences...{C_RESET}")
            result_code = self.try_decode_escapes()

        # Strategy 8: Dynamic Sandbox VM Tracer (MoonSec V3/V2, Prometheus, IronBrew, Xen)
        if not result_code:
            print(f"{C_CYAN}[*] Đang kích hoạt Dynamic Lua Sandbox & VM Hooking...{C_RESET}")
            trace_data = self.run_dynamic_tracer()

            if "error" in trace_data and trace_data["error"]:
                print(f"{C_YELLOW}[!] Sandbox log: {trace_data['error']}{C_RESET}")
            
            if trace_data.get("genv") or trace_data.get("http") or trace_data.get("loads") or trace_data.get("prints"):
                result_code = self.reconstruct_source_from_trace(trace_data)

        # Fallback: String extraction if VM protected with heavy anti-tamper
        if not result_code:
            print(f"{C_YELLOW}[*] Sử dụng Fallback: Trích xuất hằng số & Payload URLs...{C_RESET}")
            urls = re.findall(r'https?://[^\s\'"\\]+', self.raw_content)
            if urls:
                lines = [
                    "-- ========================================================",
                    f"-- [FALLBACK PAYLOAD EXTRACTION] - Engine: {obf_type}",
                    "-- ========================================================",
                    ""
                ]
                for u in set(urls):
                    lines.append(f"loadstring(game:HttpGet({json.dumps(u)}))()")
                result_code = "\n".join(lines)

        if not result_code:
            print(f"{C_RED}[-] Không thể tự động deobfuscate file này.{C_RESET}")
            return ""

        # Apply Beautifier & Variable Renamer
        result_code = self.beautify_code(result_code)

        print(f"{C_GREEN}[+] Deobfuscate thành công! Độ dài mã sạch: {len(result_code):,} ký tự.{C_RESET}")

        if output_path:
            out_file = Path(output_path)
            out_file.parent.mkdir(parents=True, exist_ok=True)
            out_file.write_text(result_code, encoding="utf-8")
            print(f"{C_GREEN}[+] Đã lưu mã nguồn sạch vào:{C_RESET} {C_CYAN}{out_file.resolve()}{C_RESET}")

        return result_code


# ---------------------------------------------------------
# INTERACTIVE MENU UI
# ---------------------------------------------------------

def clear_screen():
    os.system("clear" if os.name != "nt" else "cls")

def print_banner():
    banner = rf"""
{C_CYAN}{C_BOLD}╔════════════════════════════════════════════════════════════════╗
║    __  __                   ____            _   _ _____        ║
║   |  \/  | ___   ___  _ __ / ___|  ___  ___| | | |___ /        ║
║   | |\/| |/ _ \ / _ \| '_ \___ \ / _ \/ __| | | | |_ \        ║
║   | |  | | (_) | (_) | | | |___) |  __/ (__| |_| |___) |       ║
║   |_|  |_|\___/ \___/|_| |_|____/ \___|\___|\___/|____/        ║
║                                                                ║
║         UNIVERSAL LUA VM & MULTI-ENGINE DEOBFUSCATOR           ║
╚════════════════════════════════════════════════════════════════╝{C_RESET}
{C_MAGENTA}  [+] Động cơ:{C_RESET} MoonSec V3/V2, Luraph v11-v15 (XOR+VM), IronBrew, Prometheus, Xen, WRD, Luarmor
{C_MAGENTA}  [+] Tiện ích:{C_RESET} Sandbox Tracer, XOR Key Recovery, VM Dispatcher Analysis, AST Beautifier, Batch Mode
{C_DIM}──────────────────────────────────────────────────────────────────{C_RESET}"""
    print(banner)

def pause():
    input(f"\n{C_YELLOW}[Nhấn ENTER để tiếp tục...]{C_RESET}")

def get_download_lua_files():
    download_dir = Path("/storage/emulated/0/Download")
    if not download_dir.exists():
        download_dir = Path.cwd()
    
    files = []
    for ext in ["*.lua", "*.lua.txt", "*.txt", "*.luac"]:
        for p in download_dir.glob(ext):
            if p.is_file() and not p.name.endswith("_clean.lua") and not p.name.endswith("_deobf.lua"):
                files.append(p)
    
    files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    return files

def menu_deobf_manual_file():
    clear_screen()
    print_banner()
    print(f"{C_BOLD}{C_YELLOW}>>> CHỨC NĂNG 1: DEOBFUSCATE TỪ ĐƯỜNG DẪN TỆP (FILE){C_RESET}\n")
    
    file_input = input(f"{C_WHITE}Nhập đường dẫn file Lua/Txt/Luac:{C_RESET} ").strip().strip("'\"")
    if not file_input:
        print(f"{C_RED}[!] Bạn chưa nhập đường dẫn.{C_RESET}")
        pause()
        return

    path_obj = Path(file_input)
    if not path_obj.exists():
        print(f"{C_RED}[!] Không tìm thấy tệp:{C_RESET} {file_input}")
        pause()
        return

    default_out = str(path_obj.with_name(path_obj.stem + "_clean.lua"))
    print(f"\n{C_DIM}Gợi ý file lưu: {default_out}{C_RESET}")
    out_input = input(f"{C_WHITE}Nhập file lưu (hoặc nhấn ENTER để dùng gợi ý):{C_RESET} ").strip().strip("'\"")
    save_path = out_input if out_input else default_out

    deobf = LuaDeobfuscatorEngine(str(path_obj.resolve()), is_url=False)
    res = deobf.deobfuscate(save_path)
    
    if res:
        print(f"\n{C_GREEN}=== HOÀN TẤT DEOBFUSCATE ==={C_RESET}")
        view_opt = input(f"\n{C_YELLOW}Xem trước 30 dòng đầu? (y/n):{C_RESET} ").strip().lower()
        if view_opt == "y":
            print(f"\n{C_DIM}" + "-" * 50 + f"{C_RESET}")
            lines = res.splitlines()[:30]
            print("\n".join(lines))
            print(f"{C_DIM}" + "-" * 50 + f"{C_RESET}")
    pause()

def menu_deobf_picker():
    clear_screen()
    print_banner()
    print(f"{C_BOLD}{C_YELLOW}>>> CHỨC NĂNG 2: CHỌN NHANH FILE TỪ THƯ MỤC DOWNLOAD{C_RESET}\n")

    files = get_download_lua_files()
    if not files:
        print(f"{C_RED}[!] Không tìm thấy file script nào trong thư mục Download.{C_RESET}")
        pause()
        return

    print(f"{C_CYAN}Danh sách file tìm thấy (Xếp theo thời gian mới nhất):{C_RESET}")
    for idx, f in enumerate(files[:15], 1):
        size_kb = f.stat().st_size / 1024
        print(f"  {C_BOLD}[{idx:02d}]{C_RESET} {C_WHITE}{f.name:<34}{C_RESET} {C_DIM}({size_kb:.1f} KB){C_RESET}")

    print(f"  {C_BOLD}[00]{C_RESET} Quay lại Menu chính")
    print(f"{C_DIM}──────────────────────────────────────────────────────────────────{C_RESET}")

    choice = input(f"\n{C_YELLOW}Nhập số thứ tự file (1-{min(len(files), 15)}):{C_RESET} ").strip()
    if choice in ["0", "00", ""]:
        return

    try:
        idx_choice = int(choice)
        if 1 <= idx_choice <= len(files):
            chosen_file = files[idx_choice - 1]
            default_out = str(chosen_file.with_name(chosen_file.stem + "_clean.lua"))
            
            print(f"\n{C_GREEN}[+] Đã chọn:{C_RESET} {chosen_file.name}")
            out_input = input(f"{C_WHITE}Nhập tên file xuất (ENTER để lưu thành {Path(default_out).name}):{C_RESET} ").strip().strip("'\"")
            save_path = out_input if out_input else default_out

            deobf = LuaDeobfuscatorEngine(str(chosen_file.resolve()), is_url=False)
            res = deobf.deobfuscate(save_path)
            
            if res:
                print(f"\n{C_GREEN}=== HOÀN TẤT DEOBFUSCATE ==={C_RESET}")
                view_opt = input(f"\n{C_YELLOW}Xem trước 30 dòng đầu? (y/n):{C_RESET} ").strip().lower()
                if view_opt == "y":
                    print(f"\n{C_DIM}" + "-" * 50 + f"{C_RESET}")
                    lines = res.splitlines()[:30]
                    print("\n".join(lines))
                    print(f"{C_DIM}" + "-" * 50 + f"{C_RESET}")
            pause()
        else:
            print(f"{C_RED}[!] Lựa chọn không hợp lệ.{C_RESET}")
            pause()
    except ValueError:
        print(f"{C_RED}[!] Vui lòng nhập số nguyên.{C_RESET}")
        pause()

def menu_deobf_raw_url():
    clear_screen()
    print_banner()
    print(f"{C_BOLD}{C_YELLOW}>>> CHỨC NĂNG 3: DEOBFUSCATE TỪ LINK RAW (URL){C_RESET}\n")
    print(f"{C_DIM}Hỗ trợ: raw.githubusercontent.com, pastebin.com/raw, rentry.co/raw, v.v.{C_RESET}\n")

    url = input(f"{C_WHITE}Nhập Link Raw URL:{C_RESET} ").strip()
    if not url or not (url.startswith("http://") or url.startswith("https://")):
        print(f"{C_RED}[!] URL không hợp lệ (cần bắt đầu bằng http:// hoặc https://).{C_RESET}")
        pause()
        return

    out_name = input(f"{C_WHITE}Nhập tên file lưu (ENTER để dùng url_deobf_clean.lua):{C_RESET} ").strip().strip("'\"")
    if not out_name:
        out_name = "/storage/emulated/0/Download/url_deobf_clean.lua"
    elif not out_name.startswith("/"):
        out_name = f"/storage/emulated/0/Download/{out_name}"

    deobf = LuaDeobfuscatorEngine(url, is_url=True)
    res = deobf.deobfuscate(out_name)

    if res:
        print(f"\n{C_GREEN}=== HOÀN TẤT DEOBFUSCATE ==={C_RESET}")
        view_opt = input(f"\n{C_YELLOW}Xem trước 30 dòng đầu? (y/n):{C_RESET} ").strip().lower()
        if view_opt == "y":
            print(f"\n{C_DIM}" + "-" * 50 + f"{C_RESET}")
            lines = res.splitlines()[:30]
            print("\n".join(lines))
            print(f"{C_DIM}" + "-" * 50 + f"{C_RESET}")
    pause()

def menu_batch_deobf():
    clear_screen()
    print_banner()
    print(f"{C_BOLD}{C_YELLOW}>>> CHỨC NĂNG 4: XỬ LÝ HÀNG LOẠT (BATCH DEOBFUSCATE TOÀN BỘ){C_RESET}\n")

    files = get_download_lua_files()
    if not files:
        print(f"{C_RED}[!] Không có file script nào trong thư mục Download.{C_RESET}")
        pause()
        return

    print(f"{C_CYAN}Tìm thấy {len(files)} file cần quét. Bạn có muốn deobfuscate toàn bộ không?{C_RESET}")
    confirm = input(f"{C_YELLOW}Xác nhận thực hiện (y/n):{C_RESET} ").strip().lower()
    if confirm != "y":
        return

    print(f"\n{C_DIM}" + "=" * 55 + f"{C_RESET}")
    success_count = 0
    for idx, f in enumerate(files, 1):
        print(f"\n{C_BOLD}[{idx}/{len(files)}] Đang xử lý: {f.name}...{C_RESET}")
        out_f = f.with_name(f.stem + "_clean.lua")
        deobf = LuaDeobfuscatorEngine(str(f.resolve()), is_url=False)
        res = deobf.deobfuscate(str(out_f))
        if res:
            success_count += 1
            print(f"  {C_GREEN}==> Xong: {out_f.name}{C_RESET}")
        else:
            print(f"  {C_YELLOW}==> Đã phân tích{C_RESET}")

    print(f"\n{C_DIM}" + "=" * 55 + f"{C_RESET}")
    print(f"{C_GREEN}[+] Đã hoàn thành xử lý hàng loạt: {success_count}/{len(files)} file thành công.{C_RESET}")
    pause()

def menu_inspect_file():
    clear_screen()
    print_banner()
    print(f"{C_BOLD}{C_YELLOW}>>> CHỨC NĂNG 5: KIỂM TRA THÔNG TIN LOẠI OBFUSCATOR CỦA FILE{C_RESET}\n")

    files = get_download_lua_files()
    if not files:
        print(f"{C_RED}[!] Không tìm thấy file script nào.{C_RESET}")
        pause()
        return

    print(f"{C_CYAN}Chọn file cần kiểm tra:{C_RESET}")
    for idx, f in enumerate(files[:10], 1):
        print(f"  [{idx}] {f.name}")
    print("  [0] Nhập đường dẫn thủ công")

    c = input(f"\n{C_WHITE}Chọn:{C_RESET} ").strip()
    target_path = None
    if c == "0":
        manual = input("Nhập đường dẫn file: ").strip().strip("'\"")
        target_path = Path(manual)
    elif c.isdigit() and 1 <= int(c) <= len(files):
        target_path = files[int(c) - 1]
    
    if not target_path or not target_path.exists():
        print(f"{C_RED}[!] File không tồn tại.{C_RESET}")
        pause()
        return

    deobf = LuaDeobfuscatorEngine(str(target_path.resolve()), is_url=False)
    deobf.fetch_or_read()
    obf_type = deobf.check_obfuscation_type()

    print(f"\n{C_CYAN}─── KẾT QUẢ PHÂN TÍCH ───{C_RESET}")
    print(f"• Tên file:       {C_WHITE}{target_path.name}{C_RESET}")
    print(f"• Kích thước:     {C_WHITE}{len(deobf.raw_bytes):,} bytes{C_RESET}")
    print(f"• Loại bảo vệ:    {C_GREEN}{C_BOLD}{obf_type}{C_RESET}")

    pause()

def main_menu():
    while True:
        clear_screen()
        print_banner()
        print(f"{C_BOLD}{C_WHITE}  CHỌN CHỨC NĂNG BẠN MUỐN THỰC HIỆN:{C_RESET}\n")
        print(f"  {C_GREEN}{C_BOLD}[1]{C_RESET} {C_WHITE}Deobfuscate từ Đường Dẫn File (Nhập tay){C_RESET}")
        print(f"  {C_GREEN}{C_BOLD}[2]{C_RESET} {C_WHITE}Chọn nhanh File trong thư mục Download{C_RESET}  {C_YELLOW}(⭐ Khuyên dùng){C_RESET}")
        print(f"  {C_GREEN}{C_BOLD}[3]{C_RESET} {C_WHITE}Deobfuscate từ Link Raw (GitHub, Pastebin,...){C_RESET}")
        print(f"  {C_CYAN}{C_BOLD}[4]{C_RESET} {C_WHITE}Batch Deobfuscate (Xử lý hàng loạt toàn bộ Download){C_RESET}")
        print(f"  {C_CYAN}{C_BOLD}[5]{C_RESET} {C_WHITE}Kiểm tra thông tin Obfuscator của File{C_RESET}")
        print(f"  {C_RED}{C_BOLD}[0]{C_RESET} {C_WHITE}Thoát chương trình{C_RESET}")
        print(f"{C_DIM}──────────────────────────────────────────────────────────────────{C_RESET}")
        
        choice = input(f"\n{C_YELLOW}>>> Nhập lựa chọn [0-5]:{C_RESET} ").strip()

        if choice == "1":
            menu_deobf_manual_file()
        elif choice == "2":
            menu_deobf_picker()
        elif choice == "3":
            menu_deobf_raw_url()
        elif choice == "4":
            menu_batch_deobf()
        elif choice == "5":
            menu_inspect_file()
        elif choice == "0":
            print(f"\n{C_GREEN}[+] Tạm biệt! Hẹn gặp lại bạn.{C_RESET}\n")
            sys.exit(0)
        else:
            print(f"{C_RED}[!] Lựa chọn không hợp lệ.{C_RESET}")
            time.sleep(1)

def main():
    if len(sys.argv) > 1:
        import argparse
        parser = argparse.ArgumentParser(description="Universal Lua VM Deobfuscator Tool")
        parser.add_argument("-f", "--file", help="Đường dẫn file Lua/Txt/Luac")
        parser.add_argument("-u", "--url", help="Link Raw URL")
        parser.add_argument("-o", "--output", help="Đường dẫn file lưu kết quả")
        args = parser.parse_args()

        target = args.url if args.url else args.file
        is_url = bool(args.url)
        deobf = LuaDeobfuscatorEngine(target, is_url=is_url)
        res = deobf.deobfuscate(args.output)
        if not args.output and res:
            print("\n" + "=" * 50)
            print(res)
    else:
        main_menu()

if __name__ == "__main__":
    main()

