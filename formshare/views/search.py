import paginate

from formshare.processes.elasticsearch.user_index import get_user_index_manager
from formshare.processes.elasticsearch.partner_index import get_partner_index_manager
from formshare.views.classes import PrivateView


class APIUserSearchSelect2(PrivateView):
    def process_view(self):
        index_manager = get_user_index_manager(self.request)
        q = self.request.params.get("q", "")
        include_me = self.request.params.get("include_me", "False")
        if include_me == "False":
            include_me = False
        else:
            include_me = True
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
                    if result["user_id"] != self.userID or include_me:
                        select2_result.append(
                            {
                                "id": result["user_id"],
                                "text": result["user_name"],
                                "user_email": result.get("user_email", ""),
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


class APIPartnerSearchSelect2(PrivateView):
    def process_view(self):
        index_manager = get_partner_index_manager(self.request)
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
            query_result, total = index_manager.query_partner(q, 0, query_size)
            if total > 0:
                collection = list(range(total))
                page = paginate.Page(collection, current_page, 10)
                query_result, total = index_manager.query_partner(
                    q, page.first_item - 1, query_size
                )
                select2_result = []
                for result in query_result:
                    select2_result.append(
                        {
                            "id": result["partner_id"],
                            "text": result["partner_name"],
                            "partner_email": result.get("partner_email", ""),
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
