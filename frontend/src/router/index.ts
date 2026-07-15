import { createRouter, createWebHistory } from "vue-router";
import HomeView from "../views/HomeView.vue";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", name: "home", component: HomeView },
    {
      path: "/map",
      name: "map",
      component: () => import("../views/MapView.vue"),
    },
    {
      path: "/emotions",
      name: "emotions",
      component: () => import("../views/EmotionRecommendationView.vue"),
    },
    {
      path: "/bookmarks",
      name: "bookmarks",
      component: () => import("../views/BookmarksView.vue"),
    },
    {
      path: "/places/new",
      name: "place-create",
      component: () => import("../views/PlaceFormView.vue"),
    },
    {
      path: "/places/:id/edit",
      name: "place-edit",
      component: () => import("../views/PlaceFormView.vue"),
      props: true,
    },
    {
      path: "/places/:id/checkin",
      name: "emotion-checkin",
      component: () => import("../views/EmotionCheckinView.vue"),
      props: true,
    },
    {
      path: "/places/:id",
      name: "place-detail",
      component: () => import("../views/PlaceDetailView.vue"),
      props: true,
    },
    {
      path: "/:pathMatch(.*)*",
      name: "not-found",
      component: () => import("../views/NotFoundView.vue"),
    },
  ],
  scrollBehavior(_to, _from, savedPosition) {
    return savedPosition || { top: 0, behavior: "smooth" };
  },
});

export default router;
