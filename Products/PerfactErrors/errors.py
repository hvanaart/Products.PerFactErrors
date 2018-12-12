import OFS.interfaces
import ZPublisher.interfaces
import logging
import zExceptions
import zope.cachedescriptors.property
import zope.component

log = logging.getLogger(__name__)


try:
    from perfact.generic import get_uuid4 as uuid4
except ImportError:
    log.warn('perfact.generic not found, fallback to uuid.uuid4')
    from uuid import uuid4


class RedirectView(object):
    """Redirects in case of error."""

    def __call__(self):
        log.warn('Redirecting to root')
        base_url = self.request.base
        raise zExceptions.Redirect(base_url)


class UnauthorizedRedirectView(RedirectView):
    """Redirects except for ZMI toplevel."""

    @property
    def no_redirect(self):
        """Do not redirect at toplevel for manage and manage_main.

        This allows to login via basic auth for managers.
        """
        auth_methods = ['manage', 'manage_main']

        is_toplevel = OFS.interfaces.IApplication.providedBy(self.__parent__)
        if is_toplevel:
            # Last component of the URL:
            url = self.request.URL
            last_url_part = url.rsplit('/', 1)[1]
            if last_url_part in auth_methods:
                return True

    def __call__(self):
        if self.no_redirect:
            return
        else:
            super(UnauthorizedRedirectView, self).__call__()


class DummyView(object):
    """We need this view to prohibit the re-raise of exceptions."""

    def __call__(self,):
        """Provide dummy callable."""


class LoggingView(object):
    """Log the error and traceback."""

    def log_traceback(self):
        log.error('Logging internal server error on %s with UUID: %s',
                  self.request.other['URL'], self.uuid, exc_info=True)
        log.error('Environment: %s', self.request.environ)

    @zope.cachedescriptors.property.Lazy
    def uuid(self):
        return uuid4()

    def __call__(self, request=None):
        """Log the error and render standard error message."""
        if request is not None:
            self.request = request
        self.log_traceback()
        root = self.request['PARENTS'][-1]
        std_err_mess = root.standard_error_message_show
        return std_err_mess(uuid=self.uuid)


@zope.component.adapter(ZPublisher.interfaces.IPubFailure)
def log_and_render_error_message(event):
    """Combine logging and rendering"""
    view = LoggingView()
    event.request.response.setBody(view(request=event.request))