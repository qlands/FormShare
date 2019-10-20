from formshare.views.classes import PrivateView
from formshare.processes.elasticsearch.user_index import get_user_index_manager
import paginate


class APIUserSearchSelect2(PrivateView):
    def process_view(self):
        index_manager = get_user_index_manager(self.request)
        q = self.request.params.get("q", "")
        if q == "":
            q = None
        current_page = self.request.params.get("page")
        if current_page is None:
            current_page = 1
        query_size = 10
        self.returnRawViewResult = True
        if q is not None:
            q = q.lower()
            query_result, total = index_manager.query_user(q, 0, query_size)
            if total > 0:
                collection = list(range(total))
                page = paginate.Page(collection, current_page, 10)
                query_result, total = index_manager.query_user(
                    q, page.first_item - 1, query_size
                )
                select2_result = []
                for result in query_result:
                    if result["user_id"] != self.userID:
                        select2_result.append(
                            {
                                "id": result["user_id"],
                                "text": result["user_name"],
                                "user_email": result["user_email"],
                            }
                        )
                with_pagination = False
                if page.page_count > 1:
                    with_pagination = True
                if not with_pagination:
                    return {"total": total, "results": select2_result}
                else:
                    return {
                        "total": total,
                        "results": select2_result,
                        "pagination": {"more": True},
                    }
            else:
                return {"total": 0, "results": []}
        else:
            return {"total": 0, "results": []}
