hqDefine('sso/js/enterprise_edit_identity_provider', [
    'jquery',
    'knockout',
    'underscore',
    'hqwebapp/js/utils/email',
    "hqwebapp/js/initial_page_data",
    'sso/js/models',
    'hqwebapp/js/widgets',
], function (
    $,
    ko,
    _,
    emailUtils,
    initialPageData,
    models
) {
    $(function () {
        'use strict'
        let ssoExemptUserManager = models.linkedObjectListModel({
            asyncHandler: 'sso_exempt_users_admin',
            requestContext: {
                idpSlug: initialPageData.get('idp_slug'),
            },
            validateNewObjectFn: emailUtils.validateEmail,
        });
        $('#sso-exempt-user-manager').koApplyBindings(ssoExemptUserManager);
        ssoExemptUserManager.init();

        let ssoTestUserManager = models.linkedObjectListModel({
            asyncHandler: 'sso_test_users_admin',
            requestContext: {
                idpSlug: initialPageData.get('idp_slug'),
            },
            validateNewObjectFn: emailUtils.validateEmail,
        });
        $('#sso-test-user-manager').koApplyBindings(ssoTestUserManager);
        ssoTestUserManager.init();

        let oidcClientSecretManager = function () {
            let self = {};

            self.isClientSecretVisible = ko.observable(false);
            self.isClientSecretHidden = ko.computed(function () {
                return !self.isClientSecretVisible();
            });

            self.showClientSecret = function () {
                self.isClientSecretVisible(true);
            };

            self.hideClientSecret = function () {
                self.isClientSecretVisible(false);
            };

            return self;

        };

        let remoteUserManagementClientSecretManager = function () {
            let self = {};
            self.isCancelUpdateVisible = ko.observable(false);
            self.api_secret = "";
            self.api_expiration_date = "";


            self.isAPISecretVisible =  ko.observable(!initialPageData.get('api_secret_exists'))
            self.isAPISecretHidden = ko.computed(function () {
                return !self.isAPISecretVisible();
            });

            self.showAPISecret = function () {
                self.isAPISecretVisible(true);
                self.isCancelUpdateVisible(true);
                // Store the current API secret and expiration date before clearing them for editing.
                self.api_expiration_date = document.getElementById('id_date_api_secret_expiration').value;
                self.api_secret = document.getElementById('id_api_secret').value;
                document.getElementById('id_date_api_secret_expiration').value = '';
                document.getElementById('id_api_secret').value = '';
            };

            self.hideAPISecret = function () {
                self.isAPISecretVisible(false);
                self.isCancelUpdateVisible(false);
                // Restore the original values of the API secret and expiration date after canceling editing.
                document.getElementById('id_api_secret').value = self.api_secret;
                document.getElementById('id_date_api_secret_expiration').value = self.api_expiration_date;

            };
            return self;

        };

        if (initialPageData.get('toggle_api_secret')) {
            $('#idp').koApplyBindings(remoteUserManagementClientSecretManager);
        }


        if (initialPageData.get('toggle_client_secret')) {
            $('#idp').koApplyBindings(oidcClientSecretManager);
        }
    });
});
