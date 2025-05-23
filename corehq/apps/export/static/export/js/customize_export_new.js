import "commcarehq";
import $ from "jquery";
import { Tooltip } from "bootstrap5";
import initialPageData from "hqwebapp/js/initial_page_data";
import models from "export/js/models";
import toggles from "hqwebapp/js/toggles";
import constants from "export/js/const";

$(function () {
    var customExportView = new models.ExportInstance(
        initialPageData.get('export_instance'),
        {
            saveUrl: initialPageData.get('full_path'),
            hasExcelDashboardAccess: initialPageData.get('has_excel_dashboard_access'),
            hasDailySavedAccess: initialPageData.get('has_daily_saved_export_access'),
            formatOptions: initialPageData.get('format_options'),
            sharingOptions: initialPageData.get('sharing_options'),
            hasOtherOwner: initialPageData.get('has_other_owner'),
            numberOfAppsToProcess: initialPageData.get('number_of_apps_to_process'),
            geoProperties: initialPageData.get('geo_properties'),
        },
    );
    initialPageData.registerUrl(
        "build_schema", "/a/---/data/export/build_full_schema/",
    );
    $('#customize-export').koApplyBindings(customExportView);
    $('.export-tooltip').each(function (index, trigger) {
        new Tooltip(trigger);
    });

    if (toggles.toggleEnabled('SUPPORT_GEO_JSON_EXPORT')) {
        const exportFormat = initialPageData.get('export_instance').export_format;
        if (exportFormat === constants.EXPORT_FORMATS.GEOJSON) {
            $("#select-geo-property").show();
            $("#split-multiselects-checkbox-div").hide();
            $("#split-multiselects-checkbox").prop("checked", false);
        }

        $('#format-select').change(function () {
            const selectedValue = $(this).val();
            if (selectedValue === constants.EXPORT_FORMATS.GEOJSON) {
                $("#select-geo-property").show();
                // Hiding and unchecking this checkbox is a temporary measure
                $("#split-multiselects-checkbox-div").hide();
                $("#split-multiselects-checkbox").prop("checked", false);
            } else {
                $("#select-geo-property").hide();
                $("#split-multiselects-checkbox-div").show();
            }
        });
    }
});
