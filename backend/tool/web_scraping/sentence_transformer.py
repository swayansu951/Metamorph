"""call embedding to use EMBEDDINGMODEL\n
    structure:\n
    encode\n
    get_sentence_dimenstion\n"""
import os
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv
from huggingface_hub import login

load_dotenv()
token = os.getenv("HF_TOKEN")

if token:
    try:
        login(token=token)
    except Exception as exc:
        print(f"[-] WARNING::Hugging Face login skipped: {str(exc)}")
else:
    print("[-] WARNONG::Invalid credentials: 404 token not found!")

class EMBEDDINGMODEL:
    """ loads the model only when it will be needed to save memmory\n
        encode :(*args, **kwargs)\n
        get_sentence_dimentions : to get the dimention of the embedding
        """
    def __init__(self, model_name):
        self.model_name = model_name
        self.model = None
        load_dotenv()

    def _load(self):
        if self.model is None:
            self.model = SentenceTransformer(self.model_name)
            
        return self.model  

    def encode(self, *args, **kwargs):
        """ carries all SentenceTransformer argsa and kwargs,\n
            parameters : *args, **kwargs\n
            Ex:\n
                def embed_query(query):
                    return model.encode([query]).astype('float32')
    """
        return self._load().encode(*args , **kwargs)
    
    def get_sentence_dimension(self):
        """dimenstion of the embedder"""
        return self._load().get_sentence_embedding_dimension()
    
embedding = EMBEDDINGMODEL('all-mpnet-base-v2')