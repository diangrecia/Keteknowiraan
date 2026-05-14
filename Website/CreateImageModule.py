import cv2
import os
import uuid
import time
import hashlib
import pants
import numpy as np
from PIL import Image
from itertools import permutations
from .ProcessImage import ConvertRGB_from_array
from .ProcessImage import ConvertArrayImage
from .ProcessImage import CreateImage
from .ProcessImage import ScaleImage
from .ProcessImage import ProcesImage
from .Function import TabuSearch, RandomSearch, GreedySearch, ACO, SkorPertama


# ==============================================================
# CACHING: Cache level modul — disimpan selama aplikasi hidup
#
# Menyimpan hasil komputasi berat yang berulang untuk gambar
# yang sama. Key = hash MD5 dari isi file gambar, sehingga
# cache otomatis tidak valid jika file gambar diganti.
#
# Yang di-cache:
#   _image_data_cache  → hasil cv2.imread + ConvertRGB_from_array
#                        + ConvertArrayImage + permutations
#                        + array_split
#                        + pants.World + pants.Solver  ← OPTIMASI BARU
#
# Struktur cache entry:
#   {
#     "img_rows"   : list numpy array per baris,
#     "Array_data" : list array biner per baris,
#     "Lidi"       : list index baris,
#     "comb"       : list permutations,
#     "comb_split" : hasil np.array_split(comb, height),
#     "aco_world"  : pants.World — dibangun sekali, di-cache,
#     "aco_solver" : pants.Solver — stateless, aman di-share,
#     "height"     : tinggi gambar,
#     "width"      : lebar gambar,
#   }
# ==============================================================
_image_data_cache = {}
_MAX_CACHE_SIZE   = 10


def _get_file_hash(filepath):
    """Hitung MD5 hash dari isi file untuk dijadikan cache key."""
    hasher = hashlib.md5()
    with open(filepath, 'rb') as f:
        buf = f.read(65536)
        while buf:
            hasher.update(buf)
            buf = f.read(65536)
    return hasher.hexdigest()


def _get_cached_image_data(image_fullpath):
    """
    Ambil data gambar dari cache jika tersedia.
    Jika belum ada atau file berubah, hitung ulang dan simpan ke cache.

    pants.World dibangun di sini (sekali saat cache miss) bukan
    di _run_generator, sehingga tidak dibangun ulang tiap request.
    """
    file_hash = _get_file_hash(image_fullpath)
    cache_key = f"{image_fullpath}::{file_hash}"

    if cache_key in _image_data_cache:
        print(f"[CACHE HIT] Menggunakan data cache untuk: {os.path.basename(image_fullpath)}")
        return _image_data_cache[cache_key]

    print(f"[CACHE MISS] Menghitung data baru untuk: {os.path.basename(image_fullpath)}")

    img_cv = cv2.imread(str(image_fullpath), 1)
    if img_cv is None:
        raise ValueError(f"Gagal membaca gambar: {image_fullpath}")

    height, width, _ = img_cv.shape

    img_pil_data, Lidi, img_rows = ConvertRGB_from_array(img_cv)
    Array_data = ConvertArrayImage(img_pil_data, [])
    comb       = list(permutations(Lidi, 2))
    comb_split = np.array_split(comb, height)

    # ==============================================================
    # OPTIMASI: pants.World dibangun sekali di sini saat cache miss.
    #
    # Sebelumnya: dibangun ulang di _run_generator setiap request
    # → memakan 13–15 detik karena mengevaluasi SkorACO untuk
    #   semua pasangan dalam comb saat inisialisasi.
    #
    # Sesudah: dibangun sekali, disimpan di cache.
    # Request berikutnya dengan gambar yang sama langsung pakai
    # dari cache → bagian ini turun dari ~15 detik menjadi 0 detik.
    #
    # Array_data di-bind sebagai default argument agar tidak
    # terjadi closure yang menangkap variabel lokal yang bisa
    # berubah di iterasi cache berikutnya.
    # ==============================================================
    def _SkorACO(a, b, _Array_data=Array_data):
        s1 = SkorPertama(_Array_data[a[0]], _Array_data[a[1]])
        s2 = SkorPertama(_Array_data[b[0]], _Array_data[b[1]])
        s3 = SkorPertama(_Array_data[a[1]], _Array_data[b[0]])
        return 1 / (1 + s1 + s2 + s3)

    t_world    = time.time()
    aco_world  = pants.World(comb, _SkorACO)
    aco_solver = pants.Solver()
    print(f"[CACHE] pants.World dibangun dalam {time.time() - t_world:.2f} detik")

    data = {
        "img_rows"   : img_rows,
        "Array_data" : Array_data,
        "Lidi"       : Lidi,
        "comb"       : comb,
        "comb_split" : comb_split,
        "aco_world"  : aco_world,    # ← BARU
        "aco_solver" : aco_solver,   # ← BARU
        "height"     : height,
        "width"      : width,
    }

    if len(_image_data_cache) >= _MAX_CACHE_SIZE:
        oldest_key = next(iter(_image_data_cache))
        del _image_data_cache[oldest_key]
        print(f"[CACHE] Cache penuh, hapus entry lama: {oldest_key}")

    _image_data_cache[cache_key] = data
    print(f"[CACHE] Data tersimpan di cache. Total entry: {len(_image_data_cache)}")

    return data


def clear_image_cache(image_fullpath=None):
    """
    Hapus cache.
    Jika image_fullpath diberikan, hanya hapus cache untuk gambar itu.
    Jika None, hapus semua cache.
    """
    global _image_data_cache
    if image_fullpath is None:
        _image_data_cache = {}
        print("[CACHE] Semua cache dihapus.")
    else:
        keys_to_delete = [k for k in _image_data_cache if k.startswith(image_fullpath)]
        for k in keys_to_delete:
            del _image_data_cache[k]
        print(f"[CACHE] Cache untuk {image_fullpath} dihapus.")


class CreateImageMotif:
    def __init__(self, fullpath, namaMotif, jmlBaris, Baris, mode, username, sessionName, seed=0):
        self.fullpath    = fullpath
        self.namaMotif   = namaMotif
        self.jmlBaris    = jmlBaris
        self.Baris       = Baris
        self.mode        = mode
        self.username    = username
        self.sessionName = sessionName
        self.seed        = seed

    def imageOriginal(self):
        slice_url_path = []
        image_fullpath = self.fullpath
        folderUser     = os.path.join("media", "motif_awal", "slices")
        os.makedirs(folderUser, exist_ok=True)

        img = cv2.imread(image_fullpath, 1)
        if img is None:
            raise ValueError(f"Gagal membaca gambar dari path: {image_fullpath}")

        if self.mode == "4":
            img = cv2.resize(img, None, fx=4, fy=4, interpolation=cv2.INTER_LINEAR)

        height, width, _ = img.shape
        num_slices      = 8
        slice_height    = height // num_slices
        slices          = []
        slice_filenames = []
        slice_indices   = []
        print(f"[INFO] Ukuran gambar: {width}x{height}, dipotong menjadi {num_slices} potongan vertikal.")

        for i in range(num_slices):
            start_y   = i * slice_height
            end_y     = height if i == num_slices - 1 else (i + 1) * slice_height
            slice_img = img[start_y:end_y, 0:width]

            if slice_img is None or slice_img.size == 0:
                print(f"[WARNING] Slice {i + 1} kosong.")
                continue

            slice_name = f"slice_{i + 1}_{self.sessionName}.jpg"
            slice_path = os.path.join(folderUser, slice_name).replace("\\", "/")
            success    = cv2.imwrite(slice_path, slice_img)
            if success:
                print(f"[OK] Slice {i + 1} saved at {slice_path}")
                slices.append(slice_img)
                slice_filenames.append(slice_name)
                slice_indices.append(i + 1)
                slice_url_path.append(f"motif_awal/slices/{slice_name}")
            else:
                print(f"[ERROR] Gagal menyimpan slice {i + 1}")

        if not slices:
            raise ValueError("Semua slice gagal disimpan!")

        pil_slices   = [Image.fromarray(cv2.cvtColor(s, cv2.COLOR_BGR2RGB)) for s in slices]
        total_height = sum(im.height for im in pil_slices)
        combined_img = Image.new('RGB', (width, total_height))
        y_offset     = 0
        for im in pil_slices:
            combined_img.paste(im, (0, y_offset))
            y_offset += im.height

        hasil_akhir_path = os.path.join(folderUser, "hasil_akhir.png")
        combined_img.save(hasil_akhir_path)
        print(f"[DONE] Gabungan slice disimpan di {hasil_akhir_path}")

        return slice_filenames, slice_indices, slice_url_path

    def _run_generator(self, jmlBaris_actual):
        t_start = time.time()

        image_fullpath = self.fullpath
        image_name     = self.namaMotif
        Baris          = int(self.Baris)
        ModeGenerate   = int(self.mode)
        folderUser     = self.username

        os.makedirs(f"media/{folderUser}", exist_ok=True)

        unique_file_name = uuid.uuid4().hex
        unique           = f"{folderUser}/{unique_file_name}.png"
        image_save_path  = image_fullpath.replace(image_name, unique)

        cached = _get_cached_image_data(image_fullpath)

        img_rows   = cached["img_rows"]
        Array_data = cached["Array_data"]
        Lidi       = cached["Lidi"]
        comb_split = cached["comb_split"]

        PanjangLidi = len(Lidi) - 1

        if ModeGenerate == 1:
            _, Best_Solution = TabuSearch(PanjangLidi, Array_data, Baris, jmlBaris_actual, [])
            a = Best_Solution[0]
        elif ModeGenerate == 2:
            a = GreedySearch(PanjangLidi, comb_split, Baris, jmlBaris_actual)
        elif ModeGenerate == 3:
            a = RandomSearch(PanjangLidi, jmlBaris_actual)
        elif ModeGenerate == 4:
            # Ambil world dan solver dari cache — tidak dibangun ulang
            world  = cached["aco_world"]
            solver = cached["aco_solver"]
            a = ACO(solver, world, jmlBaris_actual)
        else:
            raise ValueError(f"Mode tidak dikenali: {ModeGenerate}")

        print(f"[TIMER] _run_generator selesai dalam {time.time() - t_start:.2f} detik")

        return a, img_rows, image_save_path, folderUser, unique_file_name

    def imageEven(self):
        t_total  = time.time()
        jmlBaris = int(self.jmlBaris) // 2

        a, img_rows, image_save_path, folderUser, unique_file_name = self._run_generator(jmlBaris)

        c      = a[::-1]
        a_full = a + c
        b      = [x + 1 for x in a_full]

        img_out = CreateImage(a_full.copy(), img_rows)
        img_pil = Image.fromarray(img_out)
        img_pil = ProcesImage(img_pil)
        img_pil = ScaleImage(img_pil)
        img_pil.save(image_save_path)

        print(f"[TIMER] imageEven total: {time.time() - t_total:.2f} detik")
        return f"/media/{folderUser}/{unique_file_name}.png", b

    def imageOdd(self):
        t_total  = time.time()
        jmlBaris = (int(self.jmlBaris) + 1) // 2

        a, img_rows, image_save_path, folderUser, unique_file_name = self._run_generator(jmlBaris)

        temp   = a[-1]
        a_body = a[:-1]
        c      = a_body[::-1]
        a_full = a_body + [temp] + c
        b      = [x + 1 for x in a_full]

        img_out = CreateImage(a_full.copy(), img_rows)
        img_pil = Image.fromarray(img_out)
        img_pil = ProcesImage(img_pil)
        img_pil = ScaleImage(img_pil)
        img_pil.save(image_save_path)

        print(f"[TIMER] imageOdd total: {time.time() - t_total:.2f} detik")
        return f"/media/{folderUser}/{unique_file_name}.png", b


# ── Fungsi utilitas tidak berubah dari versi asli ─────────────────────────

def create_grids_around_black(image_path, output_path):
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise ValueError(f"Failed to read image from path: {image_path}")

    _, binary     = cv2.threshold(img, 50, 255, cv2.THRESH_BINARY_INV)
    output_img    = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    height, width = binary.shape

    for y in range(height):
        for x in range(width):
            if binary[y, x] == 255:
                if x > 0 and binary[y, x - 1] == 0:
                    cv2.line(output_img, (x, y), (x, y), (0, 255, 0), 1)
                if x < width - 1 and binary[y, x + 1] == 0:
                    cv2.line(output_img, (x, y), (x, y), (0, 255, 0), 1)
                if y > 0 and binary[y - 1, x] == 0:
                    cv2.line(output_img, (x, y), (x, y), (0, 255, 0), 1)
                if y < height - 1 and binary[y + 1, x] == 0:
                    cv2.line(output_img, (x, y), (x, y), (0, 255, 0), 1)

    cv2.imwrite(output_path, output_img)
    return output_path


def create_lines_for_black_pixels(image_path, output_path, grid_size=5):
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise ValueError(f"Failed to read image from path: {image_path}")

    _, binary     = cv2.threshold(img, 50, 255, cv2.THRESH_BINARY_INV)
    output_img    = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    height, width = binary.shape

    for y in range(0, height, grid_size):
        start_x = None
        for x in range(width):
            if binary[y, x] == 255:
                if start_x is None:
                    start_x = x
            else:
                if start_x is not None and x - start_x > 1:
                    cv2.line(output_img, (start_x, y), (x - 1, y), (0, 255, 0), 1)
                start_x = None

    for x in range(0, width, grid_size):
        start_y = None
        for y in range(height):
            if binary[y, x] == 255:
                if start_y is None:
                    start_y = y
            else:
                if start_y is not None and y - start_y > 1:
                    cv2.line(output_img, (x, start_y), (x, y - 1), (0, 255, 0), 1)
                start_y = None

    cv2.imwrite(output_path, output_img)
    return output_path


def fill_color_on_white_click(image_path, output_path, click_position, fill_color):
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Failed to read image from path: {image_path}")

    gray      = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY)
    x, y      = click_position

    if binary[y, x] == 255:
        mask = np.zeros((binary.shape[0] + 2, binary.shape[1] + 2), np.uint8)
        cv2.floodFill(img, mask, (x, y), fill_color)

    cv2.imwrite(output_path, img)
    return output_path


def create_grid_from_motif(image_path, output_path, grid_color=(0, 255, 0), grid_thickness=1):
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise ValueError(f"Failed to read image from path: {image_path}")

    _, binary   = cv2.threshold(img, 50, 255, cv2.THRESH_BINARY_INV)
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    grid_img    = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

    for contour in contours:
        epsilon = 0.005 * cv2.arcLength(contour, True)
        approx  = cv2.approxPolyDP(contour, epsilon, True)
        cv2.drawContours(grid_img, [approx], -1, grid_color, grid_thickness)

    cv2.imwrite(output_path, grid_img)
    return output_path