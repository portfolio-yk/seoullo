export type PlaceSource = "dataset" | "user";
export type PlaceSort = "latest" | "rating" | "likes" | "distance";

export interface PlaceImage {
  id: number;
  filename: string;
  media_type: string;
  size_bytes: number;
  sort_order: number;
  url: string;
}

export interface PlaceSummary {
  id: number;
  content_id: string | null;
  source: PlaceSource;
  content_type: string;
  content_type_id: string;
  title: string;
  description: string;
  address: string;
  detail_address: string;
  longitude: number;
  latitude: number;
  image_url: string | null;
  tags: string[];
  view_count: number;
  like_count: number;
  review_count: number;
  average_rating: number;
  distance_meters: number | null;
  created_at: string;
  updated_at: string;
}

export interface PlaceDetail extends PlaceSummary {
  liked_by_me: boolean;
  address_source: string;
  zipcode: string;
  telephone: string;
  map_level: string;
  area_code: string;
  sigungu_code: string;
  category1: string;
  category2: string;
  category3: string;
  classification1: string;
  classification2: string;
  classification3: string;
  primary_image_url: string;
  thumbnail_url: string;
  copyright_code: string;
  images: PlaceImage[];
}

export interface PlaceList {
  items: PlaceSummary[];
  page: number;
  size: number;
  total: number;
  total_pages: number;
}

export interface CategoryCount {
  content_type_id: string;
  content_type: string;
  count: number;
}

export interface PlaceMapPoint {
  id: number;
  source: PlaceSource;
  content_type: string;
  content_type_id: string;
  title: string;
  address: string;
  longitude: number;
  latitude: number;
  image_url: string | null;
  view_count: number;
  like_count: number;
  review_count: number;
  average_rating: number;
  distance_meters: number | null;
}

export interface PlaceMapQuery {
  content_type_id?: string;
  ids?: number[];
  latitude?: number;
  longitude?: number;
  radius_meters?: number;
}

export interface DuplicateCandidate {
  id: number;
  title: string;
  address: string;
  latitude: number;
  longitude: number;
  distance_meters: number;
}

export interface DuplicateWarning {
  code: "DUPLICATE_PLACE_WARNING";
  message: string;
  candidates: DuplicateCandidate[];
}

export interface PlaceQuery {
  q?: string;
  content_type_id?: string;
  source?: PlaceSource;
  ids?: number[];
  sort?: PlaceSort;
  latitude?: number;
  longitude?: number;
  radius_meters?: number;
  page?: number;
  size?: number;
}

export interface Review {
  id: number;
  place_id: number;
  rating: number;
  content: string;
  like_count: number;
  liked_by_me: boolean;
  created_at: string;
  updated_at: string;
}

export interface ReviewList {
  items: Review[];
  page: number;
  size: number;
  total: number;
  total_pages: number;
}

export interface PopularTag {
  name: string;
  usage_count: number;
}

export interface AddressSearchResult {
  address: string;
  road_address: string;
  lot_address: string;
  detail_hint: string;
  zipcode: string;
  longitude: number;
  latitude: number;
}

export interface ReverseGeocodeResult {
  address: string;
  road_address: string;
  lot_address: string;
  zipcode: string;
}

export interface EmotionRecommendationRequest {
  mood: string[];
  afterFeeling: string[];
  style: string[];
  latitude?: number;
  longitude?: number;
}

export interface EmotionMatch {
  group: "mood" | "afterFeeling" | "style";
  keyword: string;
  value: number;
}

export interface EmotionRecommendationItem {
  rank: number;
  similarity: number;
  matched_keywords: EmotionMatch[];
  reason: string;
  reason_source: "openai" | "rule";
  place: PlaceSummary;
}

export interface EmotionRecommendationResponse {
  algorithm: "pinecone_cosine" | "sqlite_cosine_fallback";
  vector_dimension: number;
  weights: Record<string, number>;
  items: EmotionRecommendationItem[];
}

export interface EmotionCheckinRequest {
  place_id: number;
  before_emotion: string;
  before_intensity: number;
  after_emotion: string;
  after_intensity: number;
  travel_style: string;
}

export interface EmotionCheckinResponse extends EmotionCheckinRequest {
  id: number;
  created_at: string;
  emotion: Record<string, Record<string, number>>;
  vector_updated: boolean;
}

export type ChatRole = "user" | "assistant";

export interface ChatHistoryMessage {
  role: ChatRole;
  content: string;
}

export interface ChatSource {
  id: number;
  title: string;
  content_type: string;
  address: string;
  image_url: string | null;
  source: PlaceSource;
}

export interface ChatResponse {
  answer: string;
  retrieval_method: "pinecone_semantic" | "sqlite_keyword" | "sqlite_popular";
  answer_source: "openai" | "rule";
  sources: ChatSource[];
}
