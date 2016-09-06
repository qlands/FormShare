from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from django.shortcuts import render

from formshare.apps.logger.models import XForm
from formshare.apps.stats.utils import get_form_submissions_per_day
from django.conf import settings

@login_required
def stats(request, username=None, id_string=None):
    if id_string:
        xform = get_object_or_404(
            XForm, user=request.user, id_string__iexact=id_string)
        data = {
            'xform': xform,
            'context.submission_stats': get_form_submissions_per_day(xform),'APP_ROOT': settings.APP_ROOT
        }
    else:
        data = {'xforms': XForm.objects.filter(user=request.user),'APP_ROOT': settings.APP_ROOT}
    return render(request, 'form-stats.html', data)


@staff_member_required
def submissions(request):
    stats = {}
    stats['APP_ROOT']= settings.APP_ROOT
    stats['submission_count'] = {}
    stats['submission_count']['total_submission_count'] = 0

    users = User.objects.all()
    for user in users:
        stats['submission_count'][user.username] = 0
        stats['submission_count'][user.username] += user.instances.count()
        stats['submission_count'][
            'total_submission_count'] += user.instances.count()

    return render(request, "submissions.html", {'stats': stats})
