import requests
from bs4 import BeautifulSoup
import os
import urllib.parse
class ImagesDownloader:
    source_url=""
    def __init__(self, input_url, output_folder):
        self.input_url = input_url
        self.output_folder = output_folder

    def download_images(self):
        """
        Downloads all images from a given URL to a specified output folder.
        """
        if not os.path.exists(self.output_folder):
            os.makedirs(self.output_folder)

        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36'}
            result = requests.get(self.input_url, headers=headers)
        except requests.exceptions.RequestException as e:
            print(f"Error fetching URL {self.input_url}: {e}")
            return
        soup = BeautifulSoup(result.content.decode(), 'html.parser')
        img_tags = soup.find_all('img')

        for img in img_tags:
            img_url = img.get('data-src')
            if not img_url:
                img_url=img.get('src')

            # Handle relative URLs
            if not img_url.startswith(('http://', 'https://')):
                img_url = requests.compat.urljoin(self.source_url, img_url)

            try:
                img_data = requests.get(img_url).content
                content_size_bytes = len(img_data)
                megabytes = content_size_bytes / (1024 * 1024)
                if megabytes>0.1:
                    img_name = os.path.basename(img_url)
                    img_name=img_name.split("?")[0]
                    filename, file_extension = os.path.splitext(img_name)
                    filename_parts=filename.split("_")
                    filename_capitalized = [item.capitalize().strip() for item in filename_parts]
                    filename = " ".join(filename_capitalized)
                    filename=f'{filename}{file_extension}'
                    with open(os.path.join(self.output_folder, filename), 'wb') as f:
                        f.write(img_data)
                    print(f"Downloaded: {filename}")
            except requests.exceptions.RequestException as e:
                print(f"Error downloading image {img_url}: {e}")

def base_url(url, with_path=False):
    parsed = urllib.parse.urlparse(url)
    path   = '/'.join(parsed.path.split('/')[:-1]) if with_path else ''
    parsed = parsed._replace(path=path)
    parsed = parsed._replace(params='')
    parsed = parsed._replace(query='')
    parsed = parsed._replace(fragment='')
    return parsed.geturl()

if __name__ == "__main__":
    images_url="https://blog.designcrowd.com/article/1770/30-famous-alcohol-logos"
    user_folder=images_url.rsplit('/', 1)[-1]
    translation_table = str.maketrans('', '', "!@#$%^&*()_-+{}[]|\:\"'<>,.?/~`")
    user_folder = user_folder.translate(translation_table)
    images_folder=f"images_processing/images/{user_folder}"
    if user_folder!="TOP_WISKY":
        imagesDownloader=ImagesDownloader(images_url,images_folder)
        imagesDownloader.source_url=base_url(images_url)
        imagesDownloader.download_images()