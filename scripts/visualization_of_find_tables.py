import fitz
from sqlalchemy import null
from sqlmodel import select

from src.config import ROOT_PATH, SORTED_FILES
from src.database import get_db
from src.models import Paper

"""
Utility function for showing images.

Intended to be imported in Jupyter notebooks to display pixmap images.

Invocation: "show_image(item, title)", where item is a PyMuPDF object
which has a "get_pixmap" method, and title is an optional string.

The function executes "item.get_pixmap(dpi=150)" and show the resulting
image.


Dependencies
------------
numpy, matplotlib, pymupdf
"""


def show_image(item, title=""):
    """Display a pixmap.

    Just to display Pixmap image of "item" - ignore the man behind the curtain.

    Args:
        item: any PyMuPDF object having a "get_pixmap" method.
        title: a string to be used as image title

    Generates an RGB Pixmap from item using a constant DPI and using matplotlib
    to show it inline of the notebook.
    """
    DPI = 150  # use this resolution
    import numpy as np
    import matplotlib.pyplot as plt

    # %matplotlib inline
    pix = item.get_pixmap(dpi=DPI)
    img = np.ndarray([pix.h, pix.w, 3], dtype=np.uint8, buffer=pix.samples_mv)
    plt.figure(dpi=DPI)  # set the figure's DPI
    plt.title(title)  # set title of image
    _ = plt.imshow(img, extent=(0, pix.w * 72 / DPI, pix.h * 72 / DPI, 0))

if __name__ == '__main__':

    with get_db() as session:
        paper = session.scalar(select(Paper).where(Paper.merged_criterion_table != null()))
        doc = fitz.open(ROOT_PATH / paper.name)
        page = doc[paper.merged_table_start_page - 1]

        tabs = page.find_tables()  # detect the tables
        for i, tab in enumerate(tabs):  # iterate over all tables
            for cell in tab.header.cells:
                page.draw_rect(cell, color=fitz.pdfcolor["red"], width=0.3)
            page.draw_rect(tab.bbox, color=fitz.pdfcolor["green"])
            print(f"Table {i} column names: {tab.header.names}, external: {tab.header.external}")

        show_image(page, f"Table & Header BBoxes")