SUPPORTED_CONTENT_TYPES = {
    "12": "관광지",
    "14": "문화시설",
    "15": "축제공연행사",
    "25": "여행코스",
    "28": "레포츠",
    "32": "숙박",
    "38": "쇼핑",
}

REQUIRED_DATASET_CONTENT_TYPE_IDS = frozenset({"12", "14", "15", "25", "28", "32", "38"})

MAX_PLACE_IMAGES = 5
MAX_IMAGE_BYTES = 5 * 1024 * 1024
ALLOWED_IMAGE_MEDIA_TYPES = frozenset({"image/jpeg", "image/png", "image/webp"})
MAX_TAGS_PER_PLACE = 10
MAX_TAG_LENGTH = 6
DUPLICATE_RADIUS_METERS = 50.0
