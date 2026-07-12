"""
To store the retrieved data in a form of vector DB in the form of individual vector space for each type and contain in a json structure :
{
    "id" : "source\_chunk\_id",
    "vectors" : {
    		"text" : "......",

    		"image" : ".......",

    		"video" : ",,,,,,,,",
    	    },
    "payload" : {
    		"query":".....",
    		"URL" : ".......",
    		"title" : "pages\_title",
    		"content\_type" : "image|text|video|link",
    		"text" : '.....',
    		"media" : "image/video URL",
    		"local\_path" : "media got downloaded",
    		"source\_domain" : "domain name",
    		"timestamp" : "when did the crawling happened",
    		"rank" : "content's rank in float"
    	   }
    bm25 / text_bm25.pkl
    "media_file" : {
    		"image": "../media/
            "video" : "../media/
            }
}
Qdrant
set UUID with a UUID registry (by default use python built in library uuid) for hardcoded agent use static uuid for each agent for variable agents use variable uuids which instantly deleted after it's work done
"""
import pickle
import shutil
import os, re,json
import numpy as np
from uuid import uuid4
from pathlib import Path
from .sentence_transformer import embedding
from rank_bm25 import BM25Okapi
from datetime import datetime
from urllib.parse import urlparse
from .uuid_registry import REGISTRY
from .sentence_transformer import embedding
from typing import List, Dict, Any, Optional
from .semantic_chunker import SemanticChunker 

class searchDB:
	"""functions:\n
		- scrap_page
		- semantic_seach
		- bm25_search
		- hybrid_search
		output :
		- search result from the database
	"""
	def __init__(self, path:str=None):
		if path is None:
			self.path = Path(__file__).resolve().parents[2] / "search_db"
		else:
			self.path = Path(path).resolve()

		#Basic path define...
		self.path = Path(path)
		self.payload_path = self.path/"payload"
		self.vector_path = self.path/"vectors"
		self.media_path = self.path/"media"
		self.bm25_path = self.path/"bm25"
		# images and videos path define....
		self.images_path =  self.media_path/"images"
		self.videos_path = self.media_path/"video"
		#payload path define...
		self.text_payload_file = self.payload_path/"text_payload.json"
		self.image_payload_file = self.payload_path/"image_payload.json"
		self.video_payload_file = self.payload_path/"video_payload.json"
		#vectors path define...
		self.text_vectors_file = self.vector_path/"text_vectors.npy"
		self.image_vectors_file = self.vector_path/"image_vectors.npy"
		self.video_vectors_file = self.vector_path/"video_vectors.npy"
		#bm25 path define...
		self.texts_bm25_file = self.bm25_path/"chunks_bm25.pkl"

		self._setup_dir()
		self._load_db()

	def _setup_dir(self):
		#make every path present..
		for dir in [
			self.payload_path,
			self.videos_path,
			self.images_path,
			self.vector_path,
			self.bm25_path,
		]:
			dir.mkdir(parents=True, exist_ok=True)

	def _load_json(self, file_path:Path) -> List[Dict[str,Any]]:
		if file_path.exists():
			with open(file_path, "r", encoding="utf-8") as f:
				return json.load(f)
		return []
		
	def _save_json(self, file_path:Path, data:List[Dict[str,Any]]):
		file_path.parent.mkdir(parents=True, exist_ok=True)
		with open(file_path, "w", encoding="utf-8") as f:
			json.dump(data, f, indent=2, ensure_ascii=False)
	
	def _load_vectors(self, file_path:Path) ->np.ndarray:
		if file_path.exists():
				return np.load(file_path)# load the array 
		return np.empty((0, embedding.get_sentence_dimension()), dtype="float32")#set the empty array dimention with data type
	
	def _save_vectors(self, file_path:Path, data:np.ndarray):
		"""saves the """
		np.save(file_path, data.astype("float32"))# save the array in a binary file 
		
	def _load_db(self):
		"""loads all the payload and vectors with pickle file in it"""
		self.text_payload = self._load_json(self.text_payload_file)
		self.image_payload = self._load_json(self.image_payload_file)
		self.video_payload = self._load_json(self.video_payload_file)

		self.text_vectors = self._load_vectors(self.text_vectors_file)
		self.image_vectors = self._load_vectors(self.image_vectors_file)
		self.video_vectors = self._load_vectors(self.video_vectors_file)

		self.bm25 = None

		if self.texts_bm25_file.exists():
			with open(self.texts_bm25_file, "rb") as f:
				self.bm25 = pickle.load(f)

	def _save_all(self):
		"""save by the functions, path and the file.."""
		self._save_json(self.text_payload_file, self.text_payload)
		self._save_json(self.image_payload_file, self.image_payload)
		self._save_json(self.video_payload_file, self.video_payload)

		self._save_vectors(self.text_vectors_file, self.text_vectors)
		self._save_vectors(self.image_vectors_file, self.image_vectors)
		self._save_vectors(self.video_vectors_file, self.video_vectors)

		self.reload_bm25()

	def _tokenize(self, text:str):
		"""tokenize the texts"""
		return re.findall(r"\b\w+\b", text.lower())
	
	def reload_bm25(self):

		content = [self._tokenize(item["chunk"]) for item in self.text_payload]

		if not content:
			self.bm25 = None
		
		self.bm25 = BM25Okapi(content)

		with open(self.texts_bm25_file, "wb") as f:
			pickle.dump(self.bm25, f)
		
	def _append_vectors(self, old_vector: np.ndarray, new_vector:np.ndarray) -> np.ndarray:
		if new_vector.size == 0:
			return old_vector

		new_vector = new_vector.reshape(1,-1)

		if old_vector.shape[0] == 0:
			return new_vector

		if old_vector.shape[1] != new_vector.shape[1]:
			return old_vector
		
		return np.vstack([old_vector, new_vector])

	def _copy_media(self, file_path:Optional[str], media_type: str) -> Optional[str]:
		
		if not file_path:
			return None
		
		path = Path(file_path)

		if not path.exists():
			return None

		if media_type == "image":
			target_dir = self.images_path
		else:
			target_dir = self.videos_path
		#create the name according to the selected media type with uuid to distinguish it
		new_name = f"{uuid4()}{path.suffix}"

		target = target_dir / new_name
		shutil.copy2(path, target)

		return str(target)
	
	def scrape_page(self, data : Dict[str, Any], query :str, agent = "web_scraper") :
		"""all the output from the BS4 scraper will be the input over here"""
		agent_id = REGISTRY.get_or_create_agent(agent)

		source_url = data.get("url","")
		title = data.get('title',"")
		description = data.get("description", "")
		source_domain = data.get("source_domain", "") or urlparse(source_url).netloc
		text = data.get("text", "")
		headings = data.get("headings", "")
		table = data.get("table", "")
		links = data.get("links", [])
		images = data.get("images", [])
		videos = data.get("videos", data.get("video", []))
		rank = data.get("rank", "")
		time_stamp = datetime.now().isoformat()
		text_embedding = embedding.encode(text).astype("float32")
		chunks = SemanticChunker(text, embedding=text_embedding)

		for chunk_index, chunk in enumerate(chunks):
			if not chunk or not chunk.strip():
				continue
			vector = embedding.encode([chunk]).astype("float32")[0]	
			if vector.size == 0:
				continue
			payload = {
				"id" : str(uuid4()),
				"vector_space" : "text",
				"content_type" : "text",
				"query" : query,
				"title" : title,
				"chunk" : chunk,
				"chunk_ind" : chunk_index,
				"agent_name" : agent,
				"agent_id" : agent_id,
				"timestamp" : time_stamp,
				"source_domain" : source_domain,
				"source_url" : source_url,
				"rank" : rank,	
				"image" : [
					img.get("local_path") or img.get("media_url") for img in data.get("images", [])
				],
				"video" :[
					vid.get("local_path") or vid.get("media_url") for vid in videos
				],
			}
			self.text_payload.append(payload)
			self.text_vectors = self._append_vectors(self.text_vectors, vector)

		for image in data.get("images", []) :
			local_path = self._copy_media(image.get("local_path"), "image") # get the image from the file

			image_text = " ".join([
				image.get("alt",''),
				image.get('title', ''),
				title,
				query,
			]).strip()

			if not image_text:
				image_text = query

			vector = embedding.encode(image_text).astype("float32")

			payload = {
				"id" : str(uuid4()),
				"vector_space" : "image",
				"content_type" : "image",
				"query" : query,
				"title" : title,
				"agent_name" : agent,
				"agent_id" : agent_id,
				"timestamp" : time_stamp,
				"source_domain" : source_domain,
				"source_url" : source_url,
				"rank" : rank,	
				"media_url" : image.get("media_url"),
				"media_text" : image_text,
				"local_path" : local_path or image.get("local_path"),
			}
			self.image_payload.append(payload)
			self.image_vectors = self._append_vectors(self.image_vectors, vector)
		
		for video in videos:
			local_path = self._copy_media(video.get("local_path"), "video")

			video_text = " ".join([
				video.get("alt",''),
				video.get('title', ''),
				title,
				query,
			]).strip()

			if not video_text:
				video_text = query

			vector = embedding.encode(video_text).astype("float32")

			payload = {
				"id" : str(uuid4()),
				"vector_space" : "video",
				"content_type" : "video",
				"query" : query,
				"title" : title,
				"agent_name" : agent,
				"agent_id" : agent_id,
				"timestamp" : time_stamp,
				"source_domain" : source_domain,
				"source_url" : source_url,
				"rank" : rank,	
				"media_url" : video.get("media_url"),
				"media_text" : video_text,
				"local_path" : local_path or video.get("local_path"),
			}

			self.video_payload.append(payload)
			self.video_vectors = self._append_vectors(self.video_vectors, vector)

		self._save_all()

		return {
			"status" : "storage",
			"texts" : len(chunks),
			"images" : len(data.get("images", [])),
			"videos" : len(videos),
			"agent" : "web_scraper",
			"id" : agent_id,
		}
	# added semantic search + bm25 search, a hybrid search method to get more of the retrieved results
	def semantic_search(self, query:str, vector_space: str = "text", top_k = 6) -> List[Dict[str,Any]]:
		query_vector = embedding.encode(query).astype("float32")

		if vector_space == "text" : 
			vector = self.text_vectors
			payload = self.text_payload

		elif vector_space == "images":
			vector = self.image_vectors
			payload = self.image_payload
		
		elif vector_space == "video":
			vector = self.video_vectors
			payload = self.video_payload

		else:
			raise ValueError("Status code 4O4: Not found, vector space must be text, image and video only")
		# if no vector, then return an empty list..
		if vector.shape[0] == 0:
			return [] 

		#calculate the score (multiply)..
		score = vector@query_vector

		# get the top k by aranging it 
		top_indices = np.argsort(score)[::-1][:top_k]
		result = []
		for idx in top_indices:
			item = payload[int(idx)].copy()
			item["similarity_scores"] = float(score[int(idx)])
			result.append(item)
		
		return result

	def bm25_search(self, query:str, top_k = 6) -> List[Dict[str,Any]]: # only for the text datas..
		query_vector = embedding.encode(query).astype("float32")

		if not self.bm25 or not self.text_payload:
			return []
		
		tokenize_query = self._tokenize(query)

		score = self.bm25.get_scores(tokenize_query)
		top_indices = np.argsort(score)[::-1][:top_k]

		result = []

		for idx in top_indices:
			item = self.text_payload[int(idx)].copy()
			item['bm25_score'] = float(score[int(idx)])
			result.append(item)
		
		return result
	
	def hybrid_search(self,query:str, top_k:int=6, alpha:int=0.65) -> List[Dict[str,Any]]:
		"""RAG 4.0 methodology, retrieve score from\n
		 - semantic score and 
		 - bm25 score"""
		
		semantic_chunk = self.semantic_search(query=query, vector_space="text") # kept for only text for now.
		bm25_chunk = self.bm25_search(query=query)

		combine = {} #combine the result into it..
		final_result = [] # only keep the final result in it...

		for item in semantic_chunk:
			item_id = item.get("id", '')
			combine.setdefault(item_id, item)
			combine[item_id]["semantic_score"]= item.get("similarity_scores", 0.0)

		max_bm25_score = max([item.get("bm25_score", 0.0) for item in bm25_chunk], default=1.0) # get the max score from the scored data in bm25

		for item in bm25_chunk:
			item_id = item.get("id", '')
			combine.setdefault(item_id, item)
			norm_bm25_score = item.get("bm25_score", 0.0) / max_bm25_score if max_bm25_score else 0.0 # normalize the score got from it
			combine[item_id]["bm25_score"] = norm_bm25_score

		for item in combine.values():
			semantic_score = item.get("semantic_score", 0.0)
			bm25_score = item.get("bm25_score" , 0.0)

			item["hybrid_score"] = (alpha * semantic_score) + ((1-alpha) * bm25_score)
			final_result.append(item)

		final_result.sort(key=lambda x : x["hybrid_score"], reverse=True) # sort it in descending order
	
		return final_result[:top_k] # return onlt the top k's..
	

