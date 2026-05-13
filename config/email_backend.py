"""
Backend SMTP compatível com o Django, com suporte a hostname TLS distinto do host TCP.

Útil quando EMAIL_HOST é um CNAME (ex.: smtp.seudominio.com) e o certificado do
servidor é válido apenas para o hostname canônico (ex.: us2.smtp.mailhostbox.com).
"""

from django.conf import settings
from django.core.mail.backends.smtp import EmailBackend as DjangoEmailBackend
from django.core.mail.utils import DNS_NAME


class EmailBackend(DjangoEmailBackend):
    def open(self):
        if self.connection:
            return False

        connection_params = {"local_hostname": DNS_NAME.get_fqdn()}
        if self.timeout is not None:
            connection_params["timeout"] = self.timeout
        if self.use_ssl:
            connection_params["context"] = self.ssl_context
        try:
            self.connection = self.connection_class(
                self.host, self.port, **connection_params
            )

            if not self.use_ssl and self.use_tls:
                tls_name = (getattr(settings, "EMAIL_SMTP_TLS_SERVERNAME", "") or "").strip()
                if tls_name and tls_name != self.connection._host:
                    saved = self.connection._host
                    self.connection._host = tls_name
                    try:
                        self.connection.starttls(context=self.ssl_context)
                    finally:
                        self.connection._host = saved
                else:
                    self.connection.starttls(context=self.ssl_context)
            if self.username and self.password:
                self.connection.login(self.username, self.password)
            return True
        except OSError:
            if not self.fail_silently:
                raise
