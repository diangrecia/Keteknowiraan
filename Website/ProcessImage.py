import numpy as np
import cv2
from PIL import ImageOps, Image

def SeparateImage(img, namaDirektori):
    """DEPRECATED — tidak perlu lagi, diganti in-memory slicing."""
    pass  # Biarkan kosong untuk backward-compat, tidak dipanggil

def ConvertRGB_from_array(img_array):
    """
    Versi baru: terima numpy array langsung, tanpa disk I/O.
    Menggantikan SeparateImage + ConvertRGB + ConvertLiditoArray sekaligus.
    Mengembalikan (img_pil_list, lidi_list, img_cv_list)
    """
    height = img_array.shape[0]
    img_pil_list = []
    lidi_list = []
    img_cv_list = []

    for i in range(min(height, 72)):
        row = img_array[i:i+1, :]  # slice langsung dari array
        # PIL version untuk ConvertRGB
        pil_row = Image.fromarray(cv2.cvtColor(row, cv2.COLOR_BGR2RGB)).convert("RGBA")
        img_pil_list.append(pil_row.getdata())
        lidi_list.append(i)
        # CV version untuk ConvertLiditoArray
        img_cv_list.append(row)

    return img_pil_list, lidi_list, img_cv_list

def ConvertArrayImage(img, Array_data):
    for i in range(min(len(img), 72)):
        try:
            Baca_data = []
            datas = img[i]
            for item in datas:
                Baca_data.append(1 if (item[0] > 200 and item[1] > 200 and item[2] > 200) else 2)
            Array_data.append(Baca_data)
        except IndexError:
            break
    return Array_data

def CreateImage(a, img):
    if not a:
        return np.array([])
    result = img[a[0]]
    for idx in a[1:]:
        result = np.vstack((result, img[idx]))
    return result

def ScaleImage(img):
    return ImageOps.scale(img, 10, resample=0)

def ProcesImage(img):
    """Versi dioptimasi: numpy vectorized, bukan loop per-pixel."""
    img_rgba = img.convert("RGBA")
    arr = np.array(img_rgba, dtype=np.uint8)

    # Kondisi: R>150, G>150, B>200 → transparankan
    mask_white = (arr[:,:,0] > 150) & (arr[:,:,1] > 150) & (arr[:,:,2] > 200)
    arr[mask_white] = [255, 255, 255, 0]

    # Kondisi: R<150, G<150, B<200 → hitam penuh
    mask_black = (arr[:,:,0] < 150) & (arr[:,:,1] < 150) & (arr[:,:,2] < 200)
    arr[mask_black] = [0, 0, 0, 255]

    return Image.fromarray(arr, 'RGBA')