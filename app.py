import io
import math
import streamlit as st
import fitz  # PyMuPDF
from PIL import Image, ImageEnhance, ImageOps
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, A3, letter, legal
from reportlab.lib.utils import ImageReader

st.set_page_config(page_title="Printora | Scan & Print", page_icon="🖨️", layout="wide")

# ---------- Pinterest-inspired design ----------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Playfair+Display:wght@500;600&display=swap');
html, body, [class*="css"] {font-family:'DM Sans',sans-serif;}
.stApp {background:linear-gradient(135deg,#fbf9fd 0%,#f5eff9 55%,#fbf7f4 100%);}
.block-container {padding-top:1.5rem;max-width:1200px;}
.brand {font-family:'Playfair Display',serif;font-size:42px;color:#594276;font-weight:600;letter-spacing:-1.5px;}
.brand span {color:#b59acb;}
.tagline {color:#82758e;font-size:14px;margin-top:-8px;}
.hero {background:linear-gradient(120deg,#eee6f6,#f9edf1);padding:25px 28px;border-radius:24px;border:1px solid #e8ddef;margin:10px 0 24px;}
.hero h1 {font-family:'Playfair Display',serif;color:#49365d;font-size:32px;margin:0 0 7px;}
.hero p {color:#766982;margin:0;}
div[data-testid="stVerticalBlockBorderWrapper"] {border-radius:20px!important;border-color:#e9e0ef!important;background:rgba(255,255,255,.88);}
.stButton>button,.stDownloadButton>button {border-radius:12px;border:0;background:#60477d;color:white;font-weight:700;padding:.6rem 1rem;}
.stButton>button:hover,.stDownloadButton>button:hover {background:#49365d;color:white;}
h2,h3 {font-family:'Playfair Display',serif!important;color:#49365d!important;}
small,.hint {color:#897f91;}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="brand">printora<span>.</span></div><div class="tagline">SCAN · CUSTOMIZE · PRINT</div>', unsafe_allow_html=True)
st.markdown("""
<div class="hero">
<h1>Your little digital print studio ✧</h1>
<p>Scan with your camera, edit your pages, arrange your layout and download a print-ready PDF.</p>
</div>
""", unsafe_allow_html=True)

def image_from_upload(upload):
    raw = upload.getvalue()
    if upload.type == "application/pdf" or upload.name.lower().endswith(".pdf"):
        doc = fitz.open(stream=raw, filetype="pdf")
        pages = []
        for page in doc:
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
            pages.append(img)
        return pages
    img = Image.open(io.BytesIO(raw))
    return [ImageOps.exif_transpose(img).convert("RGB")]

def make_print_pdf(images, options):
    size_map = {"A4": A4, "A3": A3, "Letter": letter, "Legal": legal}
    page_size = size_map[options["paper"]]
    if options["orientation"] == "Landscape":
        page_size = (page_size[1], page_size[0])
    page_w, page_h = page_size
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=page_size)

    margin = options["margin"]
    usable_w, usable_h = page_w - 2*margin, page_h - 2*margin
    nup = options["nup"]
    cols = math.ceil(math.sqrt(nup))
    rows = math.ceil(nup / cols)
    cell_w, cell_h = usable_w / cols, usable_h / rows

    print_images = []
    for img in images:
        im = img.copy()
        if options["grayscale"]:
            im = ImageOps.grayscale(im).convert("RGB")
        if options["rotate"] % 360:
            im = im.rotate(-options["rotate"], expand=True)
        im = ImageEnhance.Brightness(im).enhance(options["brightness"])
        im = ImageEnhance.Contrast(im).enhance(options["contrast"])
        print_images.append(im)

    ordered = []
    for _ in range(options["copies"]):
        ordered.extend(print_images)

    for start in range(0, len(ordered), nup):
        group = ordered[start:start+nup]
        for idx, img in enumerate(group):
            col = idx % cols
            row = idx // cols
            x0 = margin + col * cell_w
            y0 = page_h - margin - (row + 1) * cell_h
            iw, ih = img.size
            scale = min(cell_w / iw, cell_h / ih)
            draw_w, draw_h = iw * scale, ih * scale
            x = x0 + (cell_w - draw_w) / 2
            y = y0 + (cell_h - draw_h) / 2
            pdf.drawImage(ImageReader(img), x, y, width=draw_w, height=draw_h, preserveAspectRatio=True, mask='auto')
            if options["page_numbers"]:
                pdf.setFont("Helvetica", 8)
                pdf.setFillColorRGB(.45, .40, .48)
                pdf.drawCentredString(x0 + cell_w/2, y0 + 5, f"Page {start + idx + 1}")
        pdf.showPage()
    pdf.save()
    buffer.seek(0)
    return buffer.getvalue()

# ---------- Input area ----------
left, right = st.columns([1, 1], gap="large")
with left:
    with st.container(border=True):
        st.subheader("01 · Scan your document")
        st.caption("Use your phone camera or upload existing pages.")
        camera_photo = st.camera_input("Take a picture of a page", help="Allow camera access when your browser asks.")
        uploads = st.file_uploader(
            "Or upload images / PDF files",
            type=["png", "jpg", "jpeg", "webp", "pdf"],
            accept_multiple_files=True
        )

with right:
    with st.container(border=True):
        st.subheader("02 · Print settings")
        color_mode = st.selectbox("Colour mode", ["Full colour", "Black & white"])
        orientation = st.selectbox("Orientation", ["Portrait", "Landscape"])
        paper = st.selectbox("Paper size", ["A4", "A3", "Letter", "Legal"])
        nup_label = st.selectbox("Pages per sheet", ["1 page", "2 pages", "4 pages", "6 pages", "9 pages", "16 pages"])
        nup = int(nup_label.split()[0])
        copies = st.number_input("Number of copies", min_value=1, max_value=99, value=1, step=1)
        margin_label = st.selectbox("Margins", ["Default", "Narrow", "Wide", "None"])
        margin = {"Default": 28, "Narrow": 12, "Wide": 48, "None": 0}[margin_label]
        st.selectbox("Print sides", ["Single-sided", "Double-sided (if supported)"], help="Duplex printing is selected in your printer's system dialog.")
        st.selectbox("Print quality", ["Standard", "Draft / save ink", "High quality"], help="Quality options depend on your printer.")
        page_numbers = st.checkbox("Add page numbers", value=False)

# ---------- Load pages ----------
pages = []
if camera_photo is not None:
    pages.extend(image_from_upload(camera_photo))
if uploads:
    for file in uploads:
        try:
            pages.extend(image_from_upload(file))
        except Exception as exc:
            st.warning(f"Could not read {file.name}: {exc}")

st.divider()
st.subheader("03 · Edit & preview")
if not pages:
    st.info("Your scanned pages will appear here. Take a photo or upload a file to get started.")
else:
    st.success(f"{len(pages)} page(s) ready")
    edit_col, preview_col = st.columns([0.8, 1.2], gap="large")
    with edit_col:
        rotate = st.selectbox("Rotate pages", [0, 90, 180, 270], format_func=lambda x: f"{x}°")
        brightness = st.slider("Brightness", 0.5, 1.8, 1.0, 0.05)
        contrast = st.slider("Contrast", 0.5, 1.8, 1.0, 0.05)
        st.caption("These edits apply to all imported pages in this starter version.")
    with preview_col:
        preview = pages[0].copy()
        if color_mode == "Black & white":
            preview = ImageOps.grayscale(preview).convert("RGB")
        if rotate:
            preview = preview.rotate(-rotate, expand=True)
        preview = ImageEnhance.Brightness(preview).enhance(brightness)
        preview = ImageEnhance.Contrast(preview).enhance(contrast)
        st.image(preview, caption="Preview · first page", use_container_width=True)

    with st.expander("View all scanned pages"):
        cols = st.columns(4)
        for i, page in enumerate(pages):
            with cols[i % 4]:
                st.image(page, caption=f"Page {i+1}", use_container_width=True)

    options = {
        "paper": paper,
        "orientation": orientation,
        "grayscale": color_mode == "Black & white",
        "nup": nup,
        "copies": int(copies),
        "margin": margin,
        "page_numbers": page_numbers,
        "rotate": rotate,
        "brightness": brightness,
        "contrast": contrast,
    }
    pdf_bytes = make_print_pdf(pages, options)
    st.markdown("### 04 · Export & print")
    st.download_button(
        "⬇️ Download print-ready PDF",
        data=pdf_bytes,
        file_name="printora_document.pdf",
        mime="application/pdf",
        use_container_width=True
    )
    st.caption("Open the downloaded PDF and choose Print. Select your connected printer, duplex, tray and device-specific options in the system print dialog.")

with st.expander("✨ More features for the next upgrade"):
    st.markdown("""
    - Automatic page-edge detection and perspective correction
    - Remove shadows, stains and blank pages
    - OCR: turn scanned notes into searchable text
    - Merge, split, reorder and compress PDFs
    - Passport / ID photo layouts and photo printing
    - Saved printer profiles and print history
    - Printer discovery through supported local-network integrations
    """)

st.markdown("<center><small>printora. · Your files are processed in this app session. No account required.</small></center>", unsafe_allow_html=True)
