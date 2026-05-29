import glob
import os
import re
import subprocess

_registry_cache         = None
_appx_cache             = None
_winget_store_cache     = None
_winget_installed_cache = None
_winget_upgrades_cache  = None

_STORE_MARKERS = ("windowsapps", "\\packages\\")


def _get_registry_apps() -> set:
    global _registry_cache
    if _registry_cache is not None:
        return _registry_cache
    _registry_cache = set()
    try:
        import winreg
        keys = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_CURRENT_USER,  r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        ]
        for hive, path in keys:
            try:
                with winreg.OpenKey(hive, path) as key:
                    for i in range(winreg.QueryInfoKey(key)[0]):
                        try:
                            with winreg.OpenKey(key, winreg.EnumKey(key, i)) as sub:
                                try:
                                    name = winreg.QueryValueEx(sub, "DisplayName")[0]
                                    _registry_cache.add(name.lower())
                                except FileNotFoundError:
                                    pass
                        except OSError:
                            pass
            except OSError:
                pass
    except ImportError:
        pass
    return _registry_cache


def _get_appx_packages() -> set:
    global _appx_cache
    if _appx_cache is not None:
        return _appx_cache
    _appx_cache = set()
    try:
        import winreg
        path = (r"Software\Classes\Local Settings\Software\Microsoft\Windows"
                r"\CurrentVersion\AppModel\Repository\Packages")
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path) as key:
            count = winreg.QueryInfoKey(key)[0]
            for i in range(count):
                try:
                    pkg_full = winreg.EnumKey(key, i)
                    _appx_cache.add(pkg_full.lower())
                    _appx_cache.add(pkg_full.split("_")[0].lower())
                except OSError:
                    pass
    except (ImportError, OSError):
        pass
    return _appx_cache


def _load_winget_cache():
    global _winget_store_cache, _winget_installed_cache
    if _winget_store_cache is not None:
        return
    _winget_store_cache     = set()
    _winget_installed_cache = set()
    try:
        result = subprocess.run(
            ["winget", "list", "--accept-source-agreements"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            creationflags=subprocess.CREATE_NO_WINDOW, timeout=20,
        )
        for line in result.stdout.splitlines():
            for part in line.split():
                if re.match(r'^[A-Z0-9]{12,}$', part):
                    _winget_store_cache.add(part.upper())
                elif ('.' in part
                      and re.match(r'^[A-Za-z0-9][A-Za-z0-9._-]{4,79}$', part)
                      and not re.match(r'^[\d.]+$', part)):
                    _winget_installed_cache.add(part.lower())
    except Exception:
        pass


def _get_winget_store_ids() -> set:
    _load_winget_cache()
    return _winget_store_cache


def _get_winget_installed() -> set:
    _load_winget_cache()
    return _winget_installed_cache


def _load_winget_upgrades_cache():
    global _winget_upgrades_cache
    if _winget_upgrades_cache is not None:
        return
    _winget_upgrades_cache = set()
    try:
        result = subprocess.run(
            ["winget", "upgrade", "--include-unknown", "--accept-source-agreements"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            creationflags=subprocess.CREATE_NO_WINDOW, timeout=30,
        )
        for line in result.stdout.splitlines():
            for part in line.split():
                if ('.' in part
                        and re.match(r'^[A-Za-z0-9][A-Za-z0-9._-]{4,79}$', part)
                        and not re.match(r'^[\d.]+$', part)):
                    _winget_upgrades_cache.add(part.lower())
    except Exception:
        pass


def _get_winget_upgrades() -> set:
    return _winget_upgrades_cache or set()


def _check_store_source(app) -> str:
    m = re.search(r'ProductId=([A-Z0-9]+)', app.get("store_url", ""), re.I)
    if m and m.group(1).upper() in _get_winget_store_ids():
        return "store"
    return "system"


def detect_installation(app) -> tuple:
    from utils import resolve_path
    for p in app.get("check_paths", []):
        resolved = resolve_path(p).replace("/", "\\")
        is_store_path = any(m in resolved.lower() for m in _STORE_MARKERS)
        if any(c in resolved for c in ["*", "?"]):
            matches = glob.glob(resolved)
            if matches:
                via_store = any(
                    any(m in h.lower() for m in _STORE_MARKERS) for h in matches
                )
                src = "store" if via_store else _check_store_source(app)
                return True, src
        elif os.path.exists(resolved):
            src = "store" if is_store_path else _check_store_source(app)
            return True, src
    reg_names = [n.lower() for n in app.get("registry_names", [])]
    if reg_names:
        installed = _get_registry_apps()
        if any(rn in entry for rn in reg_names for entry in installed):
            return True, _check_store_source(app)
    appx_names = [n.lower() for n in app.get("appx_names", [])]
    if appx_names:
        pkgs = _get_appx_packages()
        if any(n in pkgs for n in appx_names):
            return True, "store"
    winget_id = app.get("winget_id")
    if winget_id and winget_id.lower() in _get_winget_installed():
        return True, "system"
    return False, None


def is_installed(app) -> bool:
    installed, _ = detect_installation(app)
    return installed
