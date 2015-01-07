from django.conf.urls.defaults import include, patterns
# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
                       (r'^api/', include('provision.service.urls')),
                       )
