import shutil
import urllib.parse
import os
from Images_downloader import ImagesDownloader

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
    
    
    