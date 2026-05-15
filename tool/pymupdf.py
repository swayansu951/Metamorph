# All the tools for pdf editing and pdf extraction.
# every tool have its own task or set of rule.
# Focused on using mainly pymupdf for every pdf scraping taks.

import os
import pymupdf, sys
from pathlib import Path
from langchain_core.tools import tool
# import shapes_and_symbols as sas -to be added

dir = Path(__file__).resolve().parent
image_folder = dir/"images"
image_folder.mkdir(exist_ok=True)
if not image_folder:
    os.mkdir(image_folder)

class PymupdfTools:
    
    @tool
    def extract_image_from_pdf(self,pdf):
        """In this we can get the images inside the pdf by using pymupdf's inbuilt function"""
        
        doc = pymupdf.open(pdf)
        for page_index in range(len(doc)):
            page = doc[page_index]
            image = page.get_images()

        if image:
            print(f"[+] image found :{len(image)} on page index: {page}")
        else:
            print("[+] No images")

        for image_index, img in enumerate(image, start=1):
            # get the xerf of the image 
            xref = img[0]
            # create a pix map 
            pix = pymupdf.Pixmap(doc, xref)

            # convert to RGB first
            if pix.n - pix.alpha > 3:
                pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
            # save as a .png file...
            image_file = image_folder/f"page_{page_index}_image_{image_index}.png"
            pix.save(image_file)  
            pix = None

    @tool 
    def extract_vector_graph(self, pdf):
        doc = pymupdf.open(pdf)
        for page_index in range(len(doc)):
            page = doc[page_index]
            image = page.get_images()

    @tool
    def get_snap_of_pages(self,pdf):
        """In this we can take the snapshot of each page of the pdf file using the pymupdf's inbuilt function"""
        pass

    @tool
    def make_image_from_doc_pages(self,pdf):
        """In this we can create/generate images from the document using pymupdf's inbuilt function"""
        doc_open = pymupdf.open(pdf)   

    @tool 
    def add_image_2_pdf(pdf, image, x_ratio=0, y_ratio=0, w_ratio=0.5, h_ratio=0.5):
        """In this we can add image inside a pdf using pymupdf"""
        doc = pymupdf.open(pdf)
        for page in doc:
            w, h = page.rect.width, page.rect.height
            rect = pymupdf.Rect(
                    x_ratio * w,
                    y_ratio * h,
                    (x_ratio + w_ratio) * w,
                    (y_ratio + h_ratio) * h
                )
            page.insert_image(rect, filename=image)
        doc.save("output.pdf")


