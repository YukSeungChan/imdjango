# -*- coding:utf8 -*-
from django.shortcuts import render, HttpResponse, HttpResponseRedirect
from imdjango.exceptions import *


class IMView(object):
    """
    It supports make view as class. Subclass this class and implemented `process_<request.method.lower()>_request`
    If there exists common code block in method process functions, extract it to common_process

        class Foo(IMView):
            def common_process(self, request):
                ...
                return queryset

            def process_mobile_request(self, request, queryset):
                ...

            def process_get_request(self, request, queryset):
                ...
        
    You can link in urls py like

        url(r'/foo', Foo())
    """
    login_required = False
    def __call__(self, request, *args, **kwargs):
        def call_preprocessor():
            self.args = list(args)
            if hasattr(self, 'common_process'):
                preprocess_result = self.common_process(request, *args, **kwargs)
                if type(preprocess_result) == tuple:
                    return preprocess_result
                else:
                    return [preprocess_result]
        
        def call_proper_request_processor(args, kwargs):
            method_name = 'process_%s_request'%self.request.method.lower()
            if hasattr(self, method_name):
                if hasattr(self, 'common_process'):
                    return getattr(self, method_name)(request, *args)
                else:
                    return getattr(self, method_name)(request, *args, **kwargs)
            else:
                raise UnsupportedMethodError("The method '%s' is not valid method for this request."%(self.request.method))
        
        def error_response(exception):
            message = exception.message
            if request.is_ajax():
                return HttpResponse(json.dumps(dict(status=dict(code=str(exception.__class__.__name__), reason=exception.message.encode('utf8')))), mimetype='application/json')
            else:
                return render(request, 'error.html', {'error_message':message}, status=500)
            
        self.request = request
        if self.login_required == True and not request.user.is_authenticated():
            return HttpResponseRedirect('/login/?next=%s'%request.META['PATH_INFO'])
        else:
            try:
                args = call_preprocessor() or list(args)
                return call_proper_request_processor(args, kwargs)
            except IMError, exception:
                return error_response(exception)
            
    def get_file_parameter (self, parameter_name, default=None, is_required=True):
        return self.get_parameter(parameter_name, parameter_pool=self.request.FILES, default=default, is_required=is_required)        
    
    def get_post_parameter (self, parameter_name, default="", is_required=True):
        return self.get_parameter(parameter_name, parameter_pool=self.request.POST, default=default, is_required=is_required)

    def get_get_parameter (self, parameter_name, default="", is_required=True):
        return self.get_parameter(parameter_name, parameter_pool=self.request.GET, default=default, is_required=is_required)
    
    def get_parameter(self, parameter_name, parameter_pool, default="", is_required=True, error_message=u"Invalid request"):
        def get_default_parameter():
            if is_required:
                raise NoParameterError(parameter_name)
            else:
                if default == "":
                    return parameter
                else:
                    return default

        parameter = parameter_pool.get(parameter_name, "")
        if parameter == "":
            parameter = get_default_parameter()

        return parameter
