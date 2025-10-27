# -*- coding: utf-8 -*-
import os, shutil, subprocess, uuid, json, pathlib
from typing import Optional, Tuple, List

# --- YENİ IMPORTLAR (WSQ ve PIL) ---
import base64
import io
import traceback
import re
try:
    from PIL import Image
except ImportError:
    Image = None

try:
    import cv2
    import numpy as np
except ImportError:
    cv2 = None
    np = None
# --- YENİ IMPORTLAR SONU ---


NBIS_BIN = os.getenv("NBIS_BIN", "/Users/efegurmarmara/Documents/NBIS/bin")
NFIQ2 = os.getenv("NFIQ2_PATH", "/Users/efegurmarmara/Documents/NBIS/bin/nfiq2")

def _which(cmd: str) -> Optional[str]:
    cand1 = os.path.join(NBIS_BIN, cmd) if NBIS_BIN else None
    if cand1 and os.path.exists(cand1):
        return cand1
    cand2 = shutil.which(cmd)
    return cand2 if (cand2 and os.path.exists(cand2)) else None

def ensure_tools():
    missing = []
    for tool in ["mindtct", "bozorth3", "nfseg", "dwsq", "imginfo", "rdimgwh"]:
        if not _which(tool):
            missing.append(tool)
    if not (_which(os.path.basename(NFIQ2)) or os.path.exists(NFIQ2)):
        missing.append("nfiq2")
    return missing

def run_cmd(cmd: list, cwd: Optional[str] = None, timeout: int = 120) -> Tuple[int, str, str]:
    p = subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    out, err = p.communicate(timeout=timeout)
    return p.returncode, (out or "").strip(), (err or "").strip()

def save_upload_to_tmp(file_bytes: bytes, suffix: str) -> str:
    tmpdir = pathlib.Path("tmp")
    tmpdir.mkdir(parents=True, exist_ok=True)
    fpath = tmpdir / f"{uuid.uuid4().hex}{suffix}"
    with open(fpath, "wb") as f:
        f.write(file_bytes)
    return str(fpath)

def get_image_info(image_path: str) -> dict:
    imginfo = _which("imginfo")
    if not imginfo:
        raise RuntimeError("imginfo not found in NBIS_BIN or PATH")
    code, out, err = run_cmd([imginfo, image_path])
    if code != 0:
        raise RuntimeError(f"imginfo failed (code={code}): {err or out}")
    info = {}
    try:
        for line in out.splitlines():
            if ":" in line:
                key, val = line.split(":", 1)
                key = key.strip().lower()
                val = val.strip()
                if key in ["width", "height", "depth"]:
                    info[key] = int(val)
        if not all(k in info for k in ["width", "height", "depth"]):
            raise RuntimeError(f"Could not parse all dimensions from imginfo output: {out}")
        return info
    except Exception as e:
        raise RuntimeError(f"Failed to parse imginfo output ({out}): {e}")


def nfiq2_score(image_path: str) -> dict:
    nfiq2 = _which(os.path.basename(NFIQ2)) or NFIQ2
    for flag in ("-J", "-j", "--json"):
        code, out, err = run_cmd([nfiq2, flag, image_path])
        if code == 0:
            for payload in (out, err):
                if payload:
                    try: return json.loads(payload)
                    except Exception: pass
    code, out, err = run_cmd([nfiq2, image_path])
    if code != 0:
        raise RuntimeError(f"nfiq2 failed: {err or out}")
    return {"score": out.splitlines()[-1].strip()}

def mindtct_extract(image_path: str, work_base: str) -> str:
    mindtct = _which("mindtct")
    if not mindtct:
        raise RuntimeError("mindtct not found")
    print(f"[DEBUG] Running mindtct: {image_path}")
    code, out, err = run_cmd([mindtct, image_path, work_base])
    if code != 0:
        raise RuntimeError(f"mindtct failed: {err or out}")
    xyt = f"{work_base}.xyt"
    if not os.path.exists(xyt):
        raise RuntimeError("mindtct completed but .xyt not found")
    print(f"[DEBUG] Created .xyt file: {xyt}")
    return xyt

def nfseg_segment(image_path: str, out_base: str) -> str:
    nfseg = _which("nfseg")
    if not nfseg:
        return image_path
    code, out, err = run_cmd([nfseg, image_path, out_base])
    return image_path if code != 0 else image_path


# --- BU FONKSİYON SADECE STDOUT'U OKUYACAK ŞEKİLDE AYARLANDI ---
def bozorth3_score(xyt1: str, xyt2: str) -> tuple[int, list[tuple[int, int]]]:
    bozorth3 = _which("bozorth3")
    if not bozorth3:
        raise RuntimeError("bozorth3 not found")
    
    print(f"[DEBUG] Running bozorth3 -m1 {xyt1} {xyt2}")
    
    # Varsayım: Hem skor hem de eşleşmeler (eğer varsa) STDOUT'a (out) yazdırılıyor.
    code, out, err = run_cmd([bozorth3, "-m1", xyt1, xyt2])
    
    if code != 0:
        raise RuntimeError(f"bozorth3 failed (code={code}): {err or out}")

    score = 0
    pairs = []
    lines = out.splitlines()

    if not lines:
            raise RuntimeError(f"Bozorth3 STDOUT çıktısı boş. OUT='{out}', ERR='{err}'")

    try:
        score_line = lines[-1].strip()
        score = int(score_line)
        pair_lines = lines[:-1]
        for line in pair_lines:
            parts = line.strip().split()
            if len(parts) == 2:
                try:
                    pairs.append((int(parts[0]), int(parts[1])))
                except ValueError:
                    pass
    except Exception as e:
        raise RuntimeError(f"Bozorth3 STDOUT çıktısı okunamadı (OUT='{out}'): {e}")

    print(f"[DEBUG] Bozorth3 STDOUT (Eşleşmeler ve Skor): '{out}'")
    print(f"[DEBUG] Bozorth3 STDERR (Boş olmalı?): '{err}'")
    print(f"[DEBUG] Ayrıştırılan Skor (Son Satır): {score}")
    print(f"[DEBUG] Ayrıştırılan Eşleşme Sayısı (Diğer Satırlar): {len(pairs)}")
    if pairs:
        print(f"[DEBUG] İlk 5 Eşleşme: {pairs[:5]}")

    return score, pairs


def read_xyt_file(xyt_path: str) -> list[tuple[int, int]]:
    coords = []
    try:
        with open(xyt_path, 'r') as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) >= 2:
                    try:
                        coords.append((int(parts[0]), int(parts[1])))
                    except ValueError:
                        pass
    except Exception as e:
        print(f"!!! HATA: .xyt dosyası okunamadı {xyt_path}: {e}")

    print(f"[DEBUG] Read {len(coords)} minutiae coords from {xyt_path}")
    if coords:
        print(f"[DEBUG] First 5 coords: {coords[:5]}")
    return coords


def _get_image_array(file_bytes: bytes, original_suffix: str) -> Optional[np.ndarray]:
    suffix = original_suffix.lower()
    wsq_path: Optional[pathlib.Path] = None
    raw_path: Optional[pathlib.Path] = None
    
    try:
        if suffix == ".wsq":
            if not (cv2 and np): raise RuntimeError("OpenCV/Numpy bulunamadı.")
            rdimgwh_exe = _which("rdimgwh")
            dwsq_exe = _which("dwsq")
            if not rdimgwh_exe: raise RuntimeError("rdimgwh bulunamadı.")
            if not dwsq_exe: raise RuntimeError("dwsq bulunamadı.")

            wsq_path_str = save_upload_to_tmp(file_bytes, ".wsq")
            wsq_path = pathlib.Path(wsq_path_str)
            raw_path = wsq_path.with_suffix(".raw")
            
            code, out, err = run_cmd([rdimgwh_exe, str(wsq_path)])
            if code != 0: raise RuntimeError(f"rdimgwh hatası: {err or out}")
            match = re.search(r"w=(\d+)\s+h=(\d+)", out)
            if not match: raise RuntimeError(f"Boyut okunamadı: {out}")
            width, height = int(match.group(1)), int(match.group(2))

            code, out, err = run_cmd([dwsq_exe, "raw", str(wsq_path), "-raw_out"])
            if code != 0: raise RuntimeError(f"dwsq hatası: {err or out}")
            if not raw_path.exists(): raise RuntimeError("RAW dosyası oluşmadı.")

            img_data = np.fromfile(raw_path, dtype=np.uint8)
            expected_size = width * height
            if img_data.size != expected_size:
                raise RuntimeError(f"RAW boyutu ({img_data.size}) beklenenle ({expected_size}) eşleşmiyor.")
            img = img_data.reshape((height, width))
            return img

        else:
            if not Image: raise RuntimeError("Pillow bulunamadı.")
            if not np: raise RuntimeError("Numpy bulunamadı.")
            img_pil = Image.open(io.BytesIO(file_bytes))
            img_pil_gray = img_pil.convert('L')
            img_np = np.array(img_pil_gray)
            return img_np

    except Exception as e:
        print(f"!!! KRİTİK HATA: _get_image_array çöktü (uzantı: {suffix}).")
        traceback.print_exc()
        return None
    
    finally:
        try:
            if wsq_path and wsq_path.exists(): wsq_path.unlink()
            if raw_path and raw_path.exists(): raw_path.unlink()
        except Exception as e:
            print(f"Uyarı: Geçici dosyalar ({wsq_path}) silinemedi: {e}")


def convert_to_png_base64(file_bytes: bytes, original_suffix: str) -> str | None:
    # Bu fonksiyon `analyze` endpoint'i veya başkaları için kalabilir.
    try:
        img = _get_image_array(file_bytes, original_suffix)
        if img is None: return None
        is_success, buffer = cv2.imencode(".png", img)
        if not is_success: return None
        png_data = buffer.tobytes()
        b64_data = base64.b64encode(png_data).decode('utf-8')
        return f"data:image/png;base64,{b64_data}"
    except Exception as e:
        print(f"!!! HATA: convert_to_png_base64 başarısız oldu: {e}")
        traceback.print_exc()
        return None


# --- YENİ FONKSİYON: Eşleşenleri değil, TÜM NOKTALARI çizer ---
def create_all_minutiae_png_base64(
    file_bytes: bytes,
    original_suffix: str,
    xyt_file_path: str
) -> str | None:
    """
    Görüntüyü PNG'ye dönüştürür VE mindtct'nin bulduğu TÜM minutiae'ları yeşil çizer.
    """
    
    print(f"[DEBUG] Annotating image with ALL minutiae from {xyt_file_path}.")

    try:
        img_gray = _get_image_array(file_bytes, original_suffix)
        if img_gray is None:
            print("!!! HATA: _get_image_array (all_minutiae) başarısız oldu.")
            return None

        all_minutiae_coords = read_xyt_file(xyt_file_path)
        if not all_minutiae_coords:
            print(f"!!! UYARI: {xyt_file_path} için koordinat okunamadı veya boş.")
            
        img_color = cv2.cvtColor(img_gray, cv2.COLOR_GRAY2BGR)

        # --- YENİ DÖNGÜ: 'matched_indices' yerine TÜM koordinat listesinin üzerinden geç ---
        for point_coords in all_minutiae_coords:
            try:
                # point_coords zaten (x, y) formatındadır
                print(f"[DEBUG] Drawing ALL circle at {point_coords}")
                
                cv2.circle(
                    img_color,
                    center=point_coords,
                    radius=5,
                    color=(0, 255, 0), # YEŞİL
                    thickness=2
                )
            except Exception as e:
                    print(f"!!! HATA: Daire çizilirken hata: {e}")
        
        is_success, buffer = cv2.imencode(".png", img_color)
        if not is_success:
            print("!!! HATA: create_all_minutiae_png_base64'te cv2.imencode başarısız oldu.")
            return None
        
        png_data = buffer.tobytes()
        b64_data = base64.b64encode(png_data).decode('utf-8')
        return f"data:image/png;base64,{b64_data}"

    except Exception as e:
        print(f"!!! HATA: create_all_minutiae_png_base64 çöktü: {e}")
        traceback.print_exc()
        return None
