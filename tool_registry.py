from tool.pymupdf import PymupdfTools
from tool.webscraping import run_pipeline
from tool.rag_tool import RAG_router

class TOOLS:
    registry = {
        "extract_image" : PymupdfTools.extract_image_from_pdf,
        "extract_graph" : PymupdfTools.extract_vector_graph,
        "integrate_image" : PymupdfTools.add_image_2_pdf,
        "web_scraping" : run_pipeline,
        "RAG_system" : RAG_router
    }

    @classmethod
    def get_registry(cls, name):
        """retrieves a tool from the registry inside the TOOLS class"""
        
        return cls.registry.get(name)