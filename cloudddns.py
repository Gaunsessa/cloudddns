import sys
import json
import time
import requests

class Cloudflare():
   def __init__(self, key: str) -> None:
      self.key = key

   def req(self, method: str, url: str, data: dict = {}) -> dict:
      res = requests.request(
         method,
         url, 
         headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.key}"
         },
         data = json.dumps(data),
      ).json()

      if not res["success"]: raise RuntimeError(f"{method}: {url} failed! {res['errors']}")

      return res["result"]

   def verify(self) -> bool:
      try:
         self.req("GET", "https://api.cloudflare.com/client/v4/user/tokens/verify")

         return True
      except: return False

   def update_dns_record(self, zone_id: str, record_id: str, ip: str, url: str):
      self.req(
         "PUT", 
         f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{record_id}",
         {
            "content": ip,
            "name": url,
            "proxied": False,
            "type": "A",
         }
      )

   def get_dns_records(self, zone_id: str) -> dict:
      return self.req("GET", f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records")

   def get_dns_record(self, zone_id: str, url: str) -> dict:
      records = self.get_dns_records(zone_id)

      for i in records:
         if i["name"] == url:
            return i

      raise RuntimeError(f"Record not found!")

   def get_zones(self) -> dict:
      return self.req("GET", "https://api.cloudflare.com/client/v4/zones")

   def get_zone_id(self, url: str) -> str:
      zones = self.get_zones()

      for i in zones:
         if i["name"] == url:
            return i["id"]

      raise RuntimeError(f"Zone not found!")


def get_ip() -> str:
   return requests.get("http://ifconfig.io/ip").text.replace("\n", "")

def main(url: str, sub: str, token: str, delay: int):
   cloud = Cloudflare(token)

   if not cloud.verify():
      print("Invalid token!")
      exit(-1)

   try:
      zone_id = cloud.get_zone_id(url)
   except:
      print("Invalid URL!")
      exit(-1)

   try:
      record = cloud.get_dns_record(zone_id, url=f"{sub}.{url}" if sub != "@" else url)
   except:
      print("Invalid subdomain!")
      exit(-1)

   preip = record["content"]
   while True:
      try:
         ip = get_ip()
      except:
         print("No internet!")
         time.sleep(60)
         continue

      if ip != preip:
         try:
            cloud.update_dns_record(zone_id, record["id"], ip, record["name"])
            print("IP updated")
         except:
            print("DNS update failed!")
      else: print(".", end="")

      time.sleep(delay)


if __name__ == "__main__":
   if len(sys.argv) != 5:
      print(f"USAGE: {sys.argv[0]} <URL> <SUB> <TOKEN> <DELAY>")
      exit(-1)

   main(sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]))
