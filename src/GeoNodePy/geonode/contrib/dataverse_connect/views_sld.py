import json
import urllib
import logging

from django.http import HttpResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse

from shared_dataverse_information.layer_classification.forms_api import ClassifyRequestDataForm, LayerAttributeRequestForm
from geonode.contrib.dataverse_layer_metadata.forms import CheckForExistingLayerFormWorldmap
from shared_dataverse_information.shared_form_util.format_form_errors import format_errors_as_text

from geonode.contrib.dataverse_connect.layer_metadata import LayerMetadata
from geonode.contrib.dataverse_connect.dv_utils import MessageHelperJSON
from geonode.contrib.dataverse_connect.geonode_get_services import get_layer_features_definition
from geonode.contrib.dataverse_connect.sld_helper_form import SLDHelperForm
from geonode.contrib.dataverse_connect.layer_styler import LayerStyler
from geonode.contrib.dataverse_connect.layer_metadata import LayerMetadata
from geonode.contrib.basic_auth_decorator import http_basic_auth_for_api


logger = logging.getLogger("geonode.contrib.dataverse_connect.views_sld")

#from proxy.views import geoserver_rest_proxy

# http://localhost:8000/gs/rest/sldservice/geonode:boston_social_disorder_pbl/classify.xml?attribute=Violence_4&method=equalInterval&intervals=5&ramp=Gray&startColor=%23FEE5D9&endColor=%23A50F15&reverse=
#http://localhost:8000/gs/rest/sldservice/geonode:social_disorder_shapefile_zip_x7x/classify.xml?attribute=SocStrif_1&method=equalInterval&intervals=5&ramp=Gray&startColor=%23FEE5D9&endColor=%23A50F15&reverse=
#{'reverse': False, 'attribute': u'SocStrif_1', 'dataverse_installation_name': u'http://localhost:8000', 'ramp': u'Blue', 'endColor': u'#08306b', 'datafile_id': 7775, 'intervals': 5, 'layer_name': u'social_disorder_shapefile_zip_x7x', 'startColor': u'#f7fbff', 'method': u'equalInterval'}

@csrf_exempt
@http_basic_auth_for_api
def view_layer_classification_attributes(request):
    """
    Given a layer name, return attributes for that layer to be used in the GeoConnect classification form.
    """
    # Auth check embedded in params, handled by LayerAttributeRequestForm

    if not request.POST:
        json_msg = MessageHelperJSON.get_json_msg(success=False,
                                        msg="use a POST request")
        return HttpResponse(status=405, content=json_msg, content_type="application/json")

    api_form = LayerAttributeRequestForm(request.POST.dict())
    if not api_form.is_valid():
        #
        #   Invalid, send back an error message
        #
        logger.error("Classfication error import error: \n%s" % format_errors_as_text(api_form))
        json_msg = MessageHelperJSON.get_json_msg(success=False,
                                msg="Incorrect params for LayerAttributeRequestForm: <br />%s" % api_form.errors)
        return HttpResponse(status=400, content=json_msg, content_type="application/json")

    #-------------
    # Make sure this is a WorldMap layer that we're classifying
    #-------------
    f = CheckForExistingLayerFormWorldmap(request.POST)
    if not f.is_valid():    # This should always pass....
        logger.error("Unexpected form validation error in CheckForExistingLayerFormWorldmap. Errors: %s" % f.errors)
        json_msg = MessageHelperJSON.get_json_msg(success=False,
                             msg="Invalid data for classifying an existing layer.")
        return HttpResponse(status=400, content=json_msg, content_type="application/json")

    if not f.legitimate_layer_exists(request.POST):
        err_msg = "The layer to classify could not be found.  This may not be a Dataverse-created layer."
        logger.error(err_msg)
        json_msg = MessageHelperJSON.get_json_msg(success=False,
                            msg=err_msg)
        return HttpResponse(status=400, content=json_msg, content_type="application/json")


    json_msg = get_layer_features_definition(api_form.cleaned_data.get('layer_name', ''))
    return HttpResponse(content=json_msg, content_type="application/json")



@csrf_exempt
@http_basic_auth_for_api
def view_create_new_layer_style(request):
    """
    Send in a POST request with parameters that conform to the attributes in the sld_helper_form.SLDHelperForm

    Encapsulates 3 steps:
        (1) Based on parameters, create new classfication rules and embed in SLD XML
        (2) Make the classification rules the default style for the given layer
        (3) Return links to the newly styled layer -- or an error message

    :returns: JSON message with either an error or data containing links to the update classification layer

    """

    # Auth check embedded in params, handled by ClassifyRequestDataForm

    if not request.POST:
        json_msg = MessageHelperJSON.get_json_msg(success=False, msg="use a POST request")
        return HttpResponse(status=405, content=json_msg, content_type="application/json")

    print 'view_create_new_layer_style 1'

    Post_Data_As_Dict = request.POST.dict()
    api_form = ClassifyRequestDataForm(Post_Data_As_Dict)
    if not api_form.is_valid():
        print 'view_create_new_layer_style 1a'
        #
        #   Invalid, send back an error message
        #
        logger.error("Classfication error import error: \n%s" % format_errors_as_text(api_form))
        json_msg = MessageHelperJSON.get_json_msg(success=False,
                                    msg="Incorrect params for ClassifyRequestDataForm: <br />%s" % api_form.errors)

        return HttpResponse(status=400, content=json_msg, content_type="application/json")

    print 'view_create_new_layer_style 2'


    #-------------
    # Make sure this is a WorldMap layer that we're classifying
    #-------------
    f = CheckForExistingLayerFormWorldmap(request.POST)
    if not f.is_valid():    # This should always pass....
        print 'view_create_new_layer_style 2a'
        logger.error("Unexpected form validation error in CheckForExistingLayerFormWorldmap. Errors: %s" % f.errors)
        json_msg = MessageHelperJSON.get_json_msg(success=False,
                                msg="Invalid data for classifying an existing layer.")
        return HttpResponse(status=400, content=json_msg, content_type="application/json")

    print 'view_create_new_layer_style 3'
    if not f.legitimate_layer_exists(request.POST):
        print 'view_create_new_layer_style 3a'
        err_msg = "The layer to classify could not be found.  This may not be a Dataverse-created layer."
        logger.error(err_msg)
        json_msg = MessageHelperJSON.get_json_msg(success=False,
                                msg=err_msg)
        return HttpResponse(status=400, content=json_msg, content_type="application/json")

    print 'view_create_new_layer_style 4'

    # Test failing here....
    ls = LayerStyler(request.POST)
    ls.style_layer()

    print 'view_create_new_layer_style 5'
    if ls.err_found:
        print 'has an error!'
        print '\n'.join(ls.err_msgs)
    else:
        print 'not bad'

    json_msg = ls.get_json_message()    # Will determine success/failure and appropriate params
    print json_msg
    return HttpResponse(content=json_msg, content_type="application/json")

"""
cd /Users/rmp553/Documents/github-worldmap/cga-worldmap
workon cga-worldmap
django-admin.py shell


import geonode.contrib.dataverse_connect.geonode_get_services

reload(geonode.contrib.dataverse_connect.geonode_get_services)
from geonode.contrib.dataverse_connect.geonode_get_services import get_sld_xml_for_layer, get_style_name_for_layer

print get_sld_xml_for_layer('social_disorder_shapefile_zip_kr3')
print get_style_name_for_layer('social_disorder_shapefile_zip_kr3')

"""

"""
cd /Users/rmp553/Documents/github-worldmap/cga-worldmap
workon cga-worldmap
django-admin.py shell

from geonode.contrib.dataverse_connect.layer_styler import LayerStyler
from geonode.contrib.dataverse_layer_metadata.forms import CheckForExistingLayerFormWorldmap
from geonode.contrib.dataverse_connect.geonode_get_services import get_sld_rules
from geonode.contrib.dataverse_connect.style_rules_formatter import StyleRulesFormatter
from geonode.contrib.dataverse_connect.style_layer_maker import StyleLayerMaker

params = {
        "layer_name": "social_disorder_shapefile_zip_x7x",
        "dataverse_installation_name": "http://localhost:8000",
        "datafile_id": 7775,
        "endColor": "#08306b",
        "intervals": 5,
        "attribute": "SocStrif_1",
        "method": "equalInterval",
        "ramp": "Blue",
        "startColor": "#f7fbff",
        "reverse": False
    }
f = CheckForExistingLayerFormWorldmap(params)
f.is_valid()
f.legitimate_layer_exists(params)
m = f.get_latest_dataverse_layer_metadata()
m.map_layer


ls = LayerStyler(params)
sld_rule_data= ls.set_layer_name_and_get_rule_data()
ls.layer_name

sld_formatter = StyleRulesFormatter(ls.layer_name)
sld_formatter.format_sld_xml(sld_rule_data)

sld_formatter.formatted_sld_xml

slm = StyleLayerMaker(ls.layer_name)
slm.add_sld_to_layer(sld_formatter)
"""