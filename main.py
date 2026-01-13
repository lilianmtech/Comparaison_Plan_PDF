import numpy as np
import fitz  # PyMuPDF
from PIL import Image, ImageFilter
import streamlit as st
import io

url = 'https://github.com/lilianmtech/Analyse_Parallelogramme_Vitrage/blob/main/'

# Configuration de la page
st.set_page_config(page_title="Comparateur de plans PDF", layout="wide")

# Titre de l'application
st.markdown(
    """
    <h2 style='text-align: center; 
            color: #008A92; 
            font-family: Verdana; 
            font-size:35px;
            background-color: white;
            padding: 1px; 
            border-radius: 1px;'>
       Comparateur de plans PDF
    </h2>
    """,
    unsafe_allow_html=True
)
st.divider()
st.markdown("### 📁 Import des PDFs")
#---------------------------Importation des données---------------------------

st.sidebar.image(url+"logo-couleur.png?raw=true",width=200)

# --- File uploaders ---
col_upload1, col_upload2 = st.columns(2)

with col_upload1:
    pdf_file_1 = st.file_uploader("Plan version 1 (PDF)", type=["pdf"], key="pdf1")

with col_upload2:
    pdf_file_2 = st.file_uploader("Plan version 2 (PDF)", type=["pdf"], key="pdf2")


# --- PDF to image ---
def pdf_page_to_image(pdf_bytes, page_idx):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page = doc.load_page(page_idx)

    # Zoom PDF FIXÉ À 2
    mat = fitz.Matrix(2, 2)
    pix = page.get_pixmap(matrix=mat)

    return Image.frombuffer("RGB", (pix.width, pix.height), pix.samples, "raw", "RGB", 0, 1)


# --- Overlay rouge/bleu + fond blanc + traits V1 gris clair ---
def compute_overlay(img1, img2, tolerance, enhance_factor):
    # Conversion en niveaux de gris + flou
    g1 = img1.convert("L").filter(ImageFilter.GaussianBlur(radius=1))
    g2 = img2.convert("L").filter(ImageFilter.GaussianBlur(radius=1))

    arr1 = np.array(g1).astype(np.int16)
    arr2 = np.array(g2).astype(np.int16)

    # Différence brute
    diff = np.abs(arr1 - arr2)

    # Renforcement
    diff = diff * enhance_factor

    # Masque des zones modifiées
    mask = diff > tolerance
    mask3 = np.repeat(mask[..., None], 3, axis=2)

    # --- FOND BLANC ---
    background = np.full((*arr1.shape, 3), 255, dtype=np.uint8)

    # --- TRAITS V1 EN GRIS CLAIR ---
    base_gray = np.array(img1.convert("L")).astype(np.uint8)
    base_gray = np.clip(base_gray * 0.6 + 150, 0, 255).astype(np.uint8)
    base_gray_rgb = np.stack([base_gray]*3, axis=-1)

    # --- COULEURS DES MODIFICATIONS ---
    blue = np.zeros_like(background)
    blue[..., 2] = 255  # suppressions

    red = np.zeros_like(background)
    red[..., 0] = 255  # ajouts

    # Détermination ajout / suppression
    mask_v1 = np.repeat((arr1 > arr2)[..., None], 3, axis=2)

    # Construction overlay final
    overlay = background.copy()
    overlay = np.where(~mask3, base_gray_rgb, overlay)          # traits V1
    overlay = np.where(mask3, np.where(mask_v1, blue, red), overlay)  # diff

    return Image.fromarray(overlay.astype(np.uint8), mode="RGB")


# --- Main logic ---
if pdf_file_1 and pdf_file_2:
    pdf_bytes_1 = pdf_file_1.read()
    pdf_bytes_2 = pdf_file_2.read()

    doc1 = fitz.open(stream=pdf_bytes_1, filetype="pdf")
    doc2 = fitz.open(stream=pdf_bytes_2, filetype="pdf")

    max_pages = min(len(doc1), len(doc2))

    st.sidebar.header("Paramètres")

    if max_pages > 1:
        page_index = st.sidebar.slider("Page", 1, max_pages, 1)
    else:
        st.sidebar.write("Ce PDF contient une seule page.")
        page_index = 1

    # Valeurs par défaut demandées
    tolerance = st.sidebar.slider("Tolérance (épaisseur de trait)", 0, 100, 50)
    enhance = st.sidebar.slider("Renforcement des différences", 1, 10, 2)

    img1 = pdf_page_to_image(pdf_bytes_1, page_index - 1)
    img2 = pdf_page_to_image(pdf_bytes_2, page_index - 1)

    diff_img = compute_overlay(img1, img2, tolerance, enhance)

    st.subheader(f"🧩 Comparaison page {page_index}/{max_pages}")
    st.markdown(
        """
        <div style="padding: 10px; border-radius: 5px; background-color: #e8f4fd; border-left: 5px solid #2196F3;">
            En <span style="color:red;">rouge</span> ce qui a été supprimé ou modifié,
            en <span style="color:blue;">bleu</span> ce qui a été ajouté.
        </div>
        """,
        unsafe_allow_html=True
    )

    # Affichage direct
    st.image(diff_img)

    # Export PNG uniquement
    buf = io.BytesIO()
    diff_img.save(buf, format="PNG")
    png_bytes = buf.getvalue()

    st.download_button(
        "✔️ Télécharger la visualisation",
        png_bytes,
        "Plans_Comparaison.png",
        "image/png"
    )

else:
    st.info("Importe deux fichiers PDF pour commencer la comparaison.")
