import requests
import json

PINATA_JWT = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySW5mb3JtYXRpb24iOnsiaWQiOiJmYzIyYzE0Zi05Mjg1LTRhMjUtYmI0Yy1kNGNmMDFkNTFlMTUiLCJlbWFpbCI6IngxODMyMjA3Njg2NUBnbWFpbC5jb20iLCJlbWFpbF92ZXJpZmllZCI6dHJ1ZSwicGluX3BvbGljeSI6eyJyZWdpb25zIjpbeyJkZXNpcmVkUmVwbGljYXRpb25Db3VudCI6MSwiaWQiOiJGUkExIn0seyJkZXNpcmVkUmVwbGljYXRpb25Db3VudCI6MSwiaWQiOiJOWUMxIn1dLCJ2ZXJzaW9uIjoxfSwibWZhX2VuYWJsZWQiOmZhbHNlLCJzdGF0dXMiOiJBQ1RJVkUifSwiYXV0aGVudGljYXRpb25UeXBlIjoic2NvcGVkS2V5Iiwic2NvcGVkS2V5S2V5IjoiNjgzYmYzNzgxZDhiYzZkYmU0ZTAiLCJzY29wZWRLZXlTZWNyZXQiOiJkMzAxNjE2NzJiMjBhMTk1ZjZjMzdlMDk2MTdkYTMwZTE5NzllZjQyOTE5MjZlNjFlY2QyZWM2ZjFmY2ExOTc0IiwiZXhwIjoxNzkyNDY5MzAyfQ.zx1fIDiMlVzCuoG9X9zrwcCQ7S1WQAPk7rE058ujaXU"
PINATA_GATEWAY = "https://tomato-past-marsupial-678.mypinata.cloud/ipfs"

def pin_to_ipfs(data):
	
	assert isinstance(data,dict), f"Error pin_to_ipfs expects a dictionary"
    
	url = "https://api.pinata.cloud/pinning/pinJSONToIPFS"

	headers = {"Authorization": f"Bearer {PINATA_JWT}"}
    
	payload = {"pinataContent": data}
       
	response = requests.post(url, headers=headers, json=payload)

	if response.status_code != 200:
		raise Exception(f"Error pinning to IPFS: {response.text}")

	cid = response.json()["IpfsHash"]
	
	return cid

def get_from_ipfs(cid,content_type="json"):
	assert isinstance(cid,str), f"get_from_ipfs accepts a cid in the form of a string"

	url = f"{PINATA_GATEWAY}/{cid}"

	response = requests.get(url)

	if response.status_code != 200:
		raise Exception(f"Error fetching from IPFS: {response.text}")

	data = response.json()

	assert isinstance(data,dict), f"get_from_ipfs should return a dict"
	return data
