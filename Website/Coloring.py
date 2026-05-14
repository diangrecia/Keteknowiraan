import sys
import os
import json
import ast
import hashlib
import time
import importlib.util
import concurrent.futures
from typing import List, Dict
from dataclasses import dataclass
from enum import Enum

import numpy as np
import cv2
from skimage.color import hsv2rgb
from openai import OpenAI
import matplotlib.pyplot as plt

from pymoo.core.problem import Problem
from pymoo.core.callback import Callback
from pymoo.optimize import minimize
from pymoo.termination import get_termination
from pymoode.algorithms import NSDE
from pymoode.survival import RankAndCrowding

from django.conf import settings
from django.core.cache import cache
from Website.models import UlosColorThread, UlosCharacteristic

# ---- API KEY -----------------------------------------------------------------
_key_file_path = os.path.join(settings.BASE_DIR, 'static', 'ColoringFile', 'deepseek_api.txt')
with open(_key_file_path, "r") as _kf:
    api_key = _kf.readline().strip()

# ---- IN-MEMORY DB ------------------------------------------------------------
DB_ULOS_CHARACTERISTICS: Dict = {}
DB_ULOS_THREAD_COLORS: Dict = {}

# ---- TUNING PARAMETER --------------------------------------------------------
# Naikkan TOTAL_NSDE_GENERATIONS jika ingin kualitas lebih baik (tapi lebih lama)
TOTAL_NSDE_GENERATIONS = 10
NSDE_POP_SIZE          = 5
# Resolusi thumbnail untuk evaluasi NSDE. 64x64 sudah cukup untuk perbandingan
# warna. Ubah ke 96 jika motif sangat detail dan hasil kurang memuaskan.
EVAL_THUMB_SIZE        = (64, 64)
# Timeout (detik) per API call sebelum fallback deterministik dipakai
API_TIMEOUT_SECONDS    = 25
# Jumlah warna yang dikirim ke API (bukan seluruh DB)
API_COLOR_SAMPLE_SIZE  = 40


# ==============================================================================
#  DATABASE LOADER
# ==============================================================================

def load_ulos_data_from_db():
    global DB_ULOS_CHARACTERISTICS, DB_ULOS_THREAD_COLORS
    try:
        for char in UlosCharacteristic.objects.all():
            DB_ULOS_CHARACTERISTICS[char.NAME.lower()] = {
                "garis": char.garis,
                "pola": char.pola,
                "warna_dominasi": char.warna_dominasi,
                "warna_aksen": char.warna_aksen,
                "kontras_warna": char.kontras_warna,
            }
        for color in UlosColorThread.objects.all():
            h, s, v = map(int, color.hsv.split(','))
            # DB menyimpan H dalam 0-360, S dan V dalam 0-100.
            # OpenCV HSV uint8 membutuhkan H: 0-179, S: 0-255, V: 0-255
            # Konversi dilakukan di sini agar seluruh pipeline konsisten.
            h_cv  = int(round(h / 360.0 * 179))   # 0-360  -> 0-179
            s_cv  = int(round(s / 100.0 * 255))   # 0-100  -> 0-255
            v_cv  = int(round(v / 100.0 * 255))   # 0-100  -> 0-255
            DB_ULOS_THREAD_COLORS[color.CODE] = [
                min(h_cv, 179),
                min(s_cv, 255),
                min(v_cv, 255),
            ]
    except Exception:
        DB_ULOS_CHARACTERISTICS = {}
        DB_ULOS_THREAD_COLORS = {}


# ==============================================================================
#  COLOR SCHEME ANALYSIS
# ==============================================================================

class ColorSchemeType(Enum):
    MONOCHROMATIC = "Monochromatic"
    ANALOGOUS     = "Analogous"
    COMPLEMENTARY = "Complementary"
    TRIADIC       = "Triadic"
    TETRADIC      = "Tetradic"
    ACHROMATIC    = "Achromatic"


@dataclass
class Color:
    code: str
    hue: float
    saturation: float
    value: float

    def __post_init__(self):
        self.hue = self.hue % 360

    def is_achromatic(self) -> bool:
        return self.saturation <= 20

    def hue_distance(self, other: "Color") -> float:
        diff = abs(self.hue - other.hue)
        return min(diff, 360 - diff)


class UlosColorSchemeAnalyzer:
    def __init__(self):
        self.colors: Dict[str, Color] = {}
        self._load_colors_from_db()

    def _load_colors_from_db(self):
        self.colors = {
            code: Color(code, float(h), float(s), float(v))
            for code, (h, s, v) in DB_ULOS_THREAD_COLORS.items()
        }

    def refresh_colors(self):
        self._load_colors_from_db()

    def find_similar_colors(self, primary_color_code: str, count: int = 3) -> List[str]:
        if primary_color_code not in self.colors:
            return []
        primary = self.colors[primary_color_code]
        similarities = [
            (code,
             (360 - primary.hue_distance(c)) * 0.5
             + (100 - abs(primary.saturation - c.saturation)) * 0.3
             + (100 - abs(primary.value - c.value)) * 0.2)
            for code, c in self.colors.items()
            if code != primary_color_code
        ]
        similarities.sort(key=lambda x: x[1], reverse=True)
        return [code for code, _ in similarities[:count]]

    def analyze_color_scheme(self, color_codes: List[str]) -> Dict:
        if not color_codes:
            return {"scheme_type": ColorSchemeType.ACHROMATIC, "description": "No colors provided"}
        colors = [self.colors[c] for c in color_codes if c in self.colors]
        if not colors:
            return {"scheme_type": ColorSchemeType.ACHROMATIC, "description": "Invalid color codes"}

        achromatic = [c for c in colors if c.is_achromatic()]
        chromatic  = [c for c in colors if not c.is_achromatic()]

        if not chromatic:
            return {"scheme_type": ColorSchemeType.ACHROMATIC,
                    "description": "All colors are neutral",
                    "colors": color_codes, "achromatic_count": len(achromatic),
                    "chromatic_count": 0, "hue_range": 0}
        if len(chromatic) == 1:
            return {"scheme_type": ColorSchemeType.MONOCHROMATIC,
                    "description": "Single color with neutral variations",
                    "colors": color_codes, "hue_range": 0,
                    "achromatic_count": len(achromatic), "chromatic_count": 1}

        if self._is_triadic(chromatic):
            return {"scheme_type": ColorSchemeType.TRIADIC,
                    "description": "Three colors equally spaced (~120 apart)",
                    "colors": color_codes, "hue_range": self._hue_range(chromatic),
                    "achromatic_count": len(achromatic), "chromatic_count": len(chromatic)}
        if self._is_tetradic(chromatic):
            return {"scheme_type": ColorSchemeType.TETRADIC,
                    "description": "Four colors forming two complementary pairs",
                    "colors": color_codes, "hue_range": self._hue_range(chromatic),
                    "achromatic_count": len(achromatic), "chromatic_count": len(chromatic)}

        pairs = [chromatic[i].hue_distance(chromatic[j])
                 for i in range(len(chromatic)) for j in range(i+1, len(chromatic))]
        max_d = max(pairs)
        avg_d = sum(pairs) / len(pairs)

        if max_d <= 30:
            st, desc = ColorSchemeType.MONOCHROMATIC, f"Very similar hues within {max_d:.1f} deg"
        elif max_d <= 60:
            st, desc = ColorSchemeType.ANALOGOUS, f"Adjacent hues spanning {max_d:.1f} deg"
        elif any(abs(d - 180) <= 30 for d in pairs):
            st, desc = ColorSchemeType.COMPLEMENTARY, "Colors from opposite sides of color wheel"
        else:
            st, desc = ColorSchemeType.TETRADIC, "Multiple colors with complex relationships"

        return {"scheme_type": st, "description": desc, "colors": color_codes,
                "hue_range": max_d, "avg_hue_distance": avg_d,
                "achromatic_count": len(achromatic), "chromatic_count": len(chromatic)}

    def _is_triadic(self, chromatic: List[Color]) -> bool:
        if len(chromatic) != 3:
            return False
        hues  = sorted(c.hue for c in chromatic)
        dists = [abs(hues[1]-hues[0]), abs(hues[2]-hues[1]),
                 abs((hues[0]+360)-hues[2])]
        return sum(1 for d in dists if abs(d - 120) <= 30) >= 2

    def _is_tetradic(self, chromatic: List[Color]) -> bool:
        if len(chromatic) != 4:
            return False
        hues = [c.hue for c in chromatic]
        pairs = sum(
            1 for i in range(4) for j in range(i+1, 4)
            if abs(min(abs(hues[i]-hues[j]), 360-abs(hues[i]-hues[j])) - 180) <= 30
        )
        return pairs >= 1

    def _hue_range(self, colors: List[Color]) -> float:
        hues = [c.hue for c in colors]
        return max(hues) - min(hues)


ulos_color_analyzer = UlosColorSchemeAnalyzer()


# ==============================================================================
#  FALLBACK DETERMINISTIK (dipakai jika API gagal / timeout)
# ==============================================================================

def _fallback_objective_func_code() -> str:
    """
    Fungsi objektif sederhana berbasis saturation & value.
    Tidak butuh API. Dipakai otomatis jika DeepSeek tidak dapat dihubungi.
    """
    return (
        "import numpy as np\n"
        "def calculate_user_color_preferences(hsv_image):\n"
        "    unique = np.unique(hsv_image.reshape(-1, 3), axis=0)\n"
        "    sat = unique[:, 1].astype(float)\n"
        "    val = unique[:, 2].astype(float)\n"
        "    score = (np.mean(sat) / 255.0) * 0.6 + (np.mean(val) / 255.0) * 0.4\n"
        "    return float(np.clip(score, 0.0, 1.0))\n"
    )


def _fallback_color_threads(ulos_selected_color_codes) -> Dict:
    """Kembalikan warna user langsung dari DB — tidak butuh API."""
    return {
        code: DB_ULOS_THREAD_COLORS[code]
        for code in ulos_selected_color_codes
        if code in DB_ULOS_THREAD_COLORS
    }


# ==============================================================================
#  API CALLS (dengan cache + fallback + timeout)
# ==============================================================================

def _cache_key(prefix: str, *parts) -> str:
    raw = prefix + "::" + str(sorted(str(p) for p in parts))
    return "clr_" + hashlib.md5(raw.encode()).hexdigest()


def create_custom_objective_function(ulos_type_name: str, api_key: str,
                                     ulos_selected_color_codes) -> str:
    """
    Hasilkan kode fungsi objektif via DeepSeek.
    Cache 24 jam. Fallback jika API timeout/gagal.
    """
    ck = _cache_key("obj_func", ulos_type_name, *ulos_selected_color_codes)
    cached = cache.get(ck)
    if cached:
        return cached

    char            = DB_ULOS_CHARACTERISTICS.get(ulos_type_name, {})
    list_colors_hsv = [DB_ULOS_THREAD_COLORS[c] for c in ulos_selected_color_codes
                       if c in DB_ULOS_THREAD_COLORS]

    try:
        client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com",
                        timeout=API_TIMEOUT_SECONDS)
        resp = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system",
                 "content": "You are a Senior Python Programmer. Reply with executable Python code only, no markdown, no backticks."},
                {"role": "user",
                 "content": (
                     "Buat fungsi Python bernama calculate_user_color_preferences.\n"
                     f"Karakteristik Ulos: garis={char.get('garis','')}, "
                     f"pola={char.get('pola','')}, "
                     f"warna_aksen={char.get('warna_aksen','')}, "
                     f"kontras={char.get('kontras_warna','')}.\n"
                     f"Preferensi warna HSV pengguna: {list_colors_hsv}.\n"
                     "Input fungsi: citra numpy HSV (H:0-179, S:0-255, V:0-255, dtype uint8).\n"
                     "Output: float 0..1 (1=sempurna cocok dengan preferensi).\n"
                     "Hanya kode Python, tanpa penjelasan, tanpa backtick."
                 )},
            ],
        )
        code = resp.choices[0].message.content.strip()
        code = code.replace("```python", "").replace("```", "").strip()
        cache.set(ck, code, timeout=86400)
        return code
    except Exception as e:
        print(f"[Coloring] API objective func gagal ({e}), pakai fallback.")
        return _fallback_objective_func_code()


def user_color_threads(api_key: str, ulos_selected_color_codes) -> Dict:
    """
    Rekomendasikan warna benang via DeepSeek.
    Kirim maks API_COLOR_SAMPLE_SIZE warna (bukan seluruh DB).
    Fallback langsung kembalikan warna user dari DB.
    """
    ck = _cache_key("color_threads", *ulos_selected_color_codes)
    cached = cache.get(ck)
    if cached:
        return cached

    user_selected_hsv = {
        code: DB_ULOS_THREAD_COLORS[code]
        for code in ulos_selected_color_codes
        if code in DB_ULOS_THREAD_COLORS
    }
    sampled = dict(list(DB_ULOS_THREAD_COLORS.items())[:API_COLOR_SAMPLE_SIZE])

    try:
        client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com",
                        timeout=API_TIMEOUT_SECONDS)
        resp = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system",
                 "content": "You are a Senior Programmer. Reply with JSON only, no explanation."},
                {"role": "user",
                 "content": (
                     f"Dari daftar warna HSV berikut: {sampled}, "
                     f"pilih warna yang paling sesuai dengan preferensi pengguna: {user_selected_hsv}. "
                     "Kembalikan JSON dict {\"CODE\": [H,S,V]}. Tanpa keterangan tambahan."
                 )},
            ],
        )
        raw    = resp.choices[0].message.content
        result = json.loads(raw[raw.find('{'):raw.rfind('}')+1])
        cache.set(ck, result, timeout=86400)
        return result
    except Exception as e:
        print(f"[Coloring] API color threads gagal ({e}), pakai fallback.")
        return _fallback_color_threads(ulos_selected_color_codes)


# ==============================================================================
#  IMAGE UTILITIES
# ==============================================================================

def get_unique_colors(image_path: str):
    gray = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if gray is None:
        return None, None
    return gray, np.unique(gray).tolist()


def apply_coloring(gray_image: np.ndarray, color_dict: Dict) -> np.ndarray:
    """
    Warnai gambar asli (resolusi penuh) setelah optimasi selesai.
    color_dict berisi nilai HSV skala OpenCV: H:0-179, S:0-255, V:0-255
    """
    color_image = np.zeros((*gray_image.shape, 3), dtype=np.uint8)
    for gray_value, hsv in color_dict.items():
        # Normalisasi ke 0-1 sesuai skala OpenCV
        hsv_norm = np.array([[hsv[0] / 179.0,
                               hsv[1] / 255.0,
                               hsv[2] / 255.0]], dtype=np.float32)
        rgb = hsv2rgb(hsv_norm.reshape(1, 1, 3)).reshape(3) * 255
        color_image[gray_image == int(gray_value)] = rgb.astype(np.uint8)
    return color_image


def save_colored_image(color_image: np.ndarray, ulos_type: str, task_id: str) -> str:
    """Simpan gambar hasil. Nama file menyertakan task_id agar unik per request."""
    output_dir = os.path.join(settings.BASE_DIR, 'static', 'ColoringFile', 'output')
    os.makedirs(output_dir, exist_ok=True)
    fname = f"colored_ulos_{ulos_type}_{task_id[:8]}.png"
    fpath = os.path.join(output_dir, fname)
    cv2.imwrite(fpath, cv2.cvtColor(color_image, cv2.COLOR_RGB2BGR))
    return os.path.join('ColoringFile', 'output', fname).replace(os.sep, '/')


# ==============================================================================
#  METRIK — dihitung sekali dari SATU pass image (hemat konversi warna)
# ==============================================================================

def compute_all_metrics(hsv_image: np.ndarray, n_colors: int, user_pref_func) -> tuple:
    """
    OPTIMASI KUNCI: Hitung semua 5 metrik dalam 1 fungsi.
    Konversi BGR dan RGB dilakukan sekali saja — bukan 3x seperti sebelumnya.
    """
    # Konversi sekali
    img_bgr = cv2.cvtColor(hsv_image, cv2.COLOR_HSV2BGR)
    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)

    # f1: Michaelson contrast (hue channel)
    hue_ch = hsv_image[:, :, 0].astype(np.float32) / 179.0
    mn, mx = float(hue_ch.min()), float(hue_ch.max())
    f1     = (mx - mn) / (mx + mn) if (mx + mn) > 0 else 0.0

    # f2: RMS contrast via luminance
    lum = (0.0722 * img_bgr[..., 0].astype(np.float32)
           + 0.7152 * img_bgr[..., 1].astype(np.float32)
           + 0.2126 * img_bgr[..., 2].astype(np.float32))
    f2  = float(np.sqrt(np.mean((lum - lum.mean()) ** 2)))

    # f3: Colorfulness
    r  = img_rgb[..., 0].astype(np.float32)
    g  = img_rgb[..., 1].astype(np.float32)
    b  = img_rgb[..., 2].astype(np.float32)
    rg = r - g
    yb = 0.5 * (r + g) - b
    f3 = float(np.sqrt(rg.std()**2 + yb.std()**2)
               + 0.3 * np.sqrt(rg.mean()**2 + yb.mean()**2))

    # f4: Optimal unique colors
    actual_n = len(np.unique(hsv_image.reshape(-1, 3), axis=0))
    f4       = 1.0 if (actual_n - n_colors) <= 1 else 1.0 / (1.0 + abs(actual_n - n_colors))

    # f5: User preference
    f5 = float(user_pref_func(hsv_image))

    return f1, f2, f3, f4, f5


# ==============================================================================
#  NSDE PROBLEM — menggunakan THUMBNAIL untuk evaluasi
# ==============================================================================

class UlosColoringProblem(Problem):
    def __init__(self, unique_values, gray_image, n_colors,
                 dict_ulos_thread_colors, user_preference_func):
        n_unique          = len(unique_values)
        n_colors_available = len(dict_ulos_thread_colors)

        super().__init__(
            n_var=n_unique, n_obj=5, n_constr=0,
            xl=np.zeros(n_unique, dtype=int),
            xu=np.full(n_unique, n_colors_available, dtype=int),
        )

        self.unique_values = unique_values
        self.n_colors      = n_colors
        self.user_pref_func = user_preference_func

        # Pre-build color lookup array (uint8).
        # Clamp eksplisit: H<=179, S<=255, V<=255 untuk mencegah overflow uint8
        raw_colors = np.array(list(dict_ulos_thread_colors.values()), dtype=np.int32)
        raw_colors[:, 0] = np.clip(raw_colors[:, 0], 0, 179)
        raw_colors[:, 1] = np.clip(raw_colors[:, 1], 0, 255)
        raw_colors[:, 2] = np.clip(raw_colors[:, 2], 0, 255)
        self.color_array = raw_colors.astype(np.uint8)

        # OPTIMASI UTAMA: Buat thumbnail grayscale untuk evaluasi
        # Evaluasi pada gambar kecil 10-50x lebih cepat, metrik tetap valid
        thumb = cv2.resize(gray_image, EVAL_THUMB_SIZE, interpolation=cv2.INTER_AREA)
        self.thumb_gray = thumb

        # Pre-compute mask per nilai unik pada thumbnail
        self.thumb_masks = {val: (thumb == val) for val in unique_values}

    def _evaluate(self, x, out, *args, **kwargs):
        F_values  = []
        color_arr = self.color_array
        n_avail   = len(color_arr)

        for individual in x:
            idx = np.clip(individual.flatten().astype(int), 0, n_avail - 1)

            # Bangun HSV image dari thumbnail menggunakan lookup array
            hsv_img = np.zeros((*self.thumb_gray.shape, 3), dtype=np.uint8)
            for i, val in enumerate(self.unique_values):
                mask = self.thumb_masks.get(val)
                if mask is not None and mask.any():
                    hsv_img[mask] = color_arr[idx[i]]

            f1, f2, f3, f4, f5 = compute_all_metrics(
                hsv_img, self.n_colors, self.user_pref_func)
            F_values.append([-f1, -f2, -f3, -f4, -f5])

        out["F"] = np.array(F_values)


# ==============================================================================
#  NSDE RUNNER
# ==============================================================================

class NSDEProgressReporter(Callback):
    def __init__(self, update_fn):
        super().__init__()
        self.update_fn = update_fn

    def notify(self, algorithm):
        self.update_fn(algorithm.n_gen)


def run_nsde(problem, termination, callback_instance):
    nsde = NSDE(
        pop_size=NSDE_POP_SIZE,
        variant="DE/rand/1/bin",
        CR=0.7, F=0.85,
        de_repair="bounce-back",
        survival=RankAndCrowding(crowding_func="cd"),
    )
    return minimize(problem, nsde, termination,
                    seed=42, verbose=False, callback=callback_instance)


def get_best_individual(result, unique_values, available_colors):
    pf   = result.F
    obj  = -pf
    norm = np.zeros_like(obj)
    for i in range(obj.shape[1]):
        col = obj[:, i]
        mn, mx = col.min(), col.max()
        norm[:, i] = 1.0 if mx == mn else (col - mn) / (mx - mn)

    best_idx    = np.argmax(norm.sum(axis=1))
    best_indiv  = result.X[best_idx].astype(int)
    best_scores = pf[best_idx]
    best_dict   = {
        int(k): [int(available_colors[v][0]),
                 int(available_colors[v][1]),
                 int(available_colors[v][2])]
        for k, v in zip(unique_values, best_indiv)
    }
    return best_indiv, best_dict, best_scores


# ==============================================================================
#  SAFE CODE LOADER
# ==============================================================================

def _load_objective_func(code_str: str, task_id: str):
    """Validasi syntax Python lalu load fungsi objektif secara aman."""
    try:
        ast.parse(code_str)
    except SyntaxError as e:
        raise ValueError(f"Kode objektif dari API tidak valid (SyntaxError): {e}")

    custom_dir = os.path.join(settings.BASE_DIR, 'static', 'ColoringFile')
    os.makedirs(custom_dir, exist_ok=True)
    fname  = os.path.join(custom_dir, f"_obj_{task_id[:8]}.py")
    mname  = f"_coloring_obj_{task_id[:8]}"

    with open(fname, "w", encoding="utf-8") as f:
        f.write(code_str)

    spec   = importlib.util.spec_from_file_location(mname, fname)
    module = importlib.util.module_from_spec(spec)
    sys.modules[mname] = module
    spec.loader.exec_module(module)

    try:
        os.remove(fname)
    except Exception:
        pass

    return module.calculate_user_color_preferences


# ==============================================================================
#  MAIN ENTRY POINT
# ==============================================================================

def main_coloring_process(ulos_type_input, ulos_selected_color_codes_input,
                          base_image_path, task_id):
    import csv
    import threading
    from datetime import datetime, timezone

    # Progress stages
    S_START  = 1;  S_LOAD   = 5;  S_API    = 10
    S_IMPORT = 20; S_COLORS = 25; S_NSDE_S = 30
    S_NSDE_E = 88; S_RES    = 90; S_SCHEME = 93
    S_COLOR  = 95; S_SAVE   = 98; S_DONE   = 100

    start_dt = datetime.now(timezone.utc)
    t0       = time.monotonic()

    if not hasattr(main_coloring_process, "_LOG_LOCK"):
        main_coloring_process._LOG_LOCK = threading.Lock()
    log_path = os.path.join(settings.BASE_DIR, "logs", "coloring_threads.csv")

    def write_log(status, err=""):
        end_dt = datetime.now(timezone.utc)
        dur    = time.monotonic() - t0
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        row = {
            "task_id":          task_id,
            "ulos_type":        ulos_type_input,
            "motif_path":       base_image_path,
            "selected_colors":  ",".join(ulos_selected_color_codes_input or []),
            "start_time_utc":   start_dt.isoformat(),
            "end_time_utc":     end_dt.isoformat(),
            "duration_seconds": f"{dur:.3f}",
            "status":           status,
            "error_message":    err,
        }
        with main_coloring_process._LOG_LOCK:
            fe = os.path.exists(log_path)
            with open(log_path, "a", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=row.keys())
                if not fe:
                    w.writeheader()
                w.writerow(row)

    def prog(p):
        cache.set(task_id, {'progress': p}, timeout=3600)

    current_gen = 0

    def on_gen(gen):
        nonlocal current_gen
        current_gen = gen
        rng  = S_NSDE_E - S_NSDE_S
        frac = (gen / TOTAL_NSDE_GENERATIONS) * rng if TOTAL_NSDE_GENERATIONS > 0 else rng
        prog(int(S_NSDE_S + frac))

    try:
        prog(S_START)
        prog(S_LOAD)
        load_ulos_data_from_db()
        ulos_color_analyzer.refresh_colors()

        ulos_type   = ulos_type_input
        color_codes = ulos_selected_color_codes_input
        n_colors    = len(color_codes)

        # ---- PARALEL: Dua API call sekaligus ---------------------------------
        prog(S_API)
        obj_code_result   = [None]
        rec_colors_result = [None]

        def _call_obj():
            obj_code_result[0] = create_custom_objective_function(
                ulos_type, api_key, color_codes)

        def _call_colors():
            rec_colors_result[0] = user_color_threads(api_key, color_codes)

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
            concurrent.futures.wait([ex.submit(_call_obj), ex.submit(_call_colors)])
        # -----------------------------------------------------------------------

        prog(S_IMPORT)
        user_pref_func = _load_objective_func(obj_code_result[0], task_id)

        prog(S_COLORS)
        thread_colors: Dict = {}
        thread_colors.update(rec_colors_result[0])
        thread_colors.update({
            code: DB_ULOS_THREAD_COLORS[code]
            for code in color_codes
            if code in DB_ULOS_THREAD_COLORS
        })

        gray_image, unique_values = get_unique_colors(base_image_path)
        if gray_image is None:
            prog(S_DONE)
            write_log("NoImage")
            return None, None

        problem    = UlosColoringProblem(unique_values, gray_image, n_colors,
                                         thread_colors, user_pref_func)
        terminator = get_termination("n_gen", TOTAL_NSDE_GENERATIONS)
        callback   = NSDEProgressReporter(on_gen)

        prog(S_NSDE_S)
        result = run_nsde(problem, terminator, callback)
        prog(S_NSDE_E)

        prog(S_RES)
        best_indiv, best_color_dict, best_scores = get_best_individual(
            result, unique_values, list(thread_colors.values()))

        prog(S_SCHEME)
        hsv_to_code = {tuple(v): k for k, v in DB_ULOS_THREAD_COLORS.items()}
        used_codes  = sorted(set(
            hsv_to_code[tuple(hsv)]
            for hsv in best_color_dict.values()
            if tuple(hsv) in hsv_to_code
        ))
        scheme = ulos_color_analyzer.analyze_color_scheme(used_codes)

        prog(S_COLOR)
        colored_rgb = apply_coloring(gray_image, best_color_dict)

        prog(S_SAVE)
        rel_path = save_colored_image(colored_rgb, ulos_type, task_id)

        final = {
            'progress': S_DONE,
            'status': 'Completed',
            'colored_image_url': rel_path,
            'unique_used_color_codes': used_codes,
            'color_scheme_analysis': {
                'scheme_type':      scheme['scheme_type'].value,
                'description':      scheme['description'],
                'hue_range':        scheme.get('hue_range', 0),
                'achromatic_count': scheme.get('achromatic_count', 0),
                'chromatic_count':  scheme.get('chromatic_count', 0),
            },
            'optimization_scores': {
                'michaelson_contrast':   float(-best_scores[0]),
                'rms_contrast':          float(-best_scores[1]),
                'colorfulness':          float(-best_scores[2]),
                'optimal_unique_colors': float(-best_scores[3]),
                'user_preference_match': float(-best_scores[4]),
            },
        }
        cache.set(task_id, final, timeout=3600)
        write_log("Completed")
        return rel_path, used_codes, scheme

    except Exception as e:
        err = str(e)
        print(f"[Coloring] ERROR: {err}")
        cache.set(task_id, {
            'progress':      S_DONE,
            'status':        'Error',
            'error_message': err,
        }, timeout=3600)
        write_log("Error", err)
        return None, None, None, None


if __name__ == '__main__':
    pass