from loader import dp
from .album_handler import AlbumMiddleware

if __name__ == "middlewares":
    dp.middleware.setup(AlbumMiddleware())