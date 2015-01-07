from django.conf.urls.defaults import patterns, include

API_V1 = patterns('provision.service.views',
                  (r'^preset\.json$', 'preset.show_preset_v1'),
                 )

API_V2 = patterns('provision.service.views',
                  (r'^provision\.json$', 'preset.show_preset_v2'),
                 )
                
API_V3 = patterns('provision.service.views',
                  (r'^provision\.json$', 'preset.show_preset_v3'),
                 )

urlpatterns = patterns('provision.service.views',
                       (r'^1/', include(API_V1)),
                       (r'^2/', include(API_V2)),
                       (r'^3/', include(API_V3)),
                       )

