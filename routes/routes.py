# Retic
from retic import Router

# Controllers
import controllers.novelfull as novelfull

router = Router()

router.get("/novels", novelfull.get_all_search)

router.get("/novels/chapters", novelfull.get_chapters_by_slug)
router.post("/novels/chapters", novelfull.get_chapters_by_slug)