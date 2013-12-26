
from PyQt4.QtCore import QVariant
from qgis.core import (
    QgsField,
    QgsVectorLayer,
    QgsFeature,
    QgsRectangle,
    QgsFeatureRequest,
    QgsGeometry,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform
)

from safe.common.utilities import OrderedDict
from safe.impact_functions.core import FunctionProvider
from safe.impact_functions.core import get_hazard_layer, get_exposure_layer
from safe.impact_functions.core import get_question
from safe.common.tables import Table, TableRow
from safe.common.utilities import ugettext as tr
from safe.storage.vector import Vector
from safe_qgis.utilities.utilities import get_utm_epsg
from safe_qgis.exceptions import InvalidParameterError


class FloodNativePolygonExperimentalFunction(FunctionProvider):
    """
    Simple experimental impact function for inundation
    (polygon-polygon)

    :author Dmitry Kolesov
    :rating 1
    :param requires category=='hazard' and \
                    subcategory in ['flood', 'tsunami'] and \
                    layertype=='vector'
    :param requires category=='exposure' and \
                    subcategory in ['structure'] and \
                    layertype=='vector'
    """

    title = tr('Be-flooded')

    parameters = OrderedDict([
        # This field of impact layer marks inundated roads by '1' value
        ('target_field', 'flooded'),
        # This field of the exposure layer contains
        # information about building types
        ('building_type_field', 'TYPE'),
        # This field of the  hazard layer contains information
        # about inundated areas
        ('affected_field', 'FLOODPRONE'),
        # This value in 'affected_field' of the hazard layer
        # marks the areas as inundated
        ('affected_value', 'YES'),
    ])

    def get_function_type(self):
        """Get type of the impact function.

        :returns:   'qgis2.0'
        """
        return 'qgis2.0'

    def set_extent(self, extent):
        """
        Set up the extent of area of interest ([xmin, ymin, xmax, ymax]).

        Mandatory method.
        """
        self.extent = extent

    def run(self, layers):
        """
        Experimental impact function

        Input
          layers: List of layers expected to contain
              H: Polygon layer of inundation areas
              E: Vector layer of roads
        """
        target_field = self.parameters['target_field']
        building_type_field = self.parameters['building_type_field']
        affected_field = self.parameters['affected_field']
        affected_value = self.parameters['affected_value']

        # Extract data
        H = get_hazard_layer(layers)    # Flood
        E = get_exposure_layer(layers)  # Roads

        question = get_question(H.get_name(),
                                E.get_name(),
                                self)

        H = H.as_qgis_native()
        h_provider = H.dataProvider()
        affected_field_index = h_provider.fieldNameIndex(affected_field)
        if affected_field_index == -1:
            message = tr('''Parameter "Affected Field"(='%s')
                doesn't presented in the
                attribute table of the hazard layer.''' % (affected_field, ))
            raise InvalidParameterError(message)

        E = E.as_qgis_native()
        srs = E.crs().toWkt()
        e_provider = E.dataProvider()
        fields = e_provider.fields()
        # If target_field does not exist, add it:
        if fields.indexFromName(target_field) == -1:
            e_provider.addAttributes([QgsField(target_field,
                                               QVariant.Int)])
        target_field_index = e_provider.fieldNameIndex(target_field)
        fields = e_provider.fields()

        # Create layer for store the lines from E and extent
        building_layer = QgsVectorLayer(
            'Polygon?crs=' + srs, 'impact_buildings', 'memory')
        building_provider = building_layer.dataProvider()

        # Set attributes
        building_provider.addAttributes(fields.toList())
        building_layer.startEditing()
        building_layer.commitChanges()

        # Filter geometry and data using the extent
        extent = QgsRectangle(*self.extent)
        request = QgsFeatureRequest()
        request.setFilterRect(extent)

        # Split building_layer by H and save as result:
        #   1) Filter from H inundated features
        #   2) Mark buildings as inundated (1) or not inundated (0)

        affected_field_type = \
            h_provider.fields()[affected_field_index].typeName()
        if affected_field_type in ['Real', 'Integer']:
            affected_value = float(affected_value)

        h_data = H.getFeatures(request)
        hazard_poly = None
        for mpolygon in h_data:
            attrs = mpolygon.attributes()
            if attrs[affected_field_index] != affected_value:
                continue
            if hazard_poly is None:
                hazard_poly = QgsGeometry(mpolygon.geometry())
            else:
                # Make geometry union of inundated polygons

                # But some mpolygon.geometry() could be invalid, skip them
                tmp_geometry = hazard_poly.combine(mpolygon.geometry())
                try:
                    if tmp_geometry.isGeosValid():
                        hazard_poly = tmp_geometry
                except AttributeError:
                    pass

        if hazard_poly is None:
            message = tr('''There are no objects
                in the hazard layer with
                "Affected value"='%s'.
                Please check the value or use other
                extent.''' % (affected_value, ))
            raise InvalidParameterError(message)

        e_data = E.getFeatures(request)
        for feat in e_data:
            building_geom = feat.geometry()
            attrs = feat.attributes()
            l_feat = QgsFeature()
            l_feat.setGeometry(building_geom)
            l_feat.setAttributes(attrs)
            if hazard_poly.intersects(building_geom):
                l_feat.setAttribute(target_field_index, 1)
            else:

                l_feat.setAttribute(target_field_index, 0)
            (_, __) = \
                    building_layer.dataProvider().addFeatures([l_feat])
        building_layer.updateExtents()

        # Generate simple impact report

        building_count = flooded_count = 0  # Count of buildings
        buildings_by_type = dict()      # Length of flooded roads by types

        buildings_data = building_layer.getFeatures()
        building_type_field_index = \
            building_layer.fieldNameIndex(building_type_field)
        for building in buildings_data:
            building_count += 1
            attrs = building.attributes()
            building_type = attrs[building_type_field_index]
            if building_type in [None,
                                 'NULL', 'null',
                                 'Null'
            ]:
                building_type = 'Unknown type'

            if not building_type in buildings_by_type:
                buildings_by_type[building_type] = {'flooded': 0, 'total': 0}
            buildings_by_type[building_type]['total'] += 1

            if attrs[target_field_index] == 1:
                flooded_count += 1
                buildings_by_type[building_type]['flooded'] += 1

        table_body = [question,
                      TableRow([tr('Building Type'),
                                tr('Flooded'),
                                tr('Total')],
                               header=True),
                      TableRow([tr('All'),
                                int(flooded_count),
                                int(building_count)])]
        table_body.append(TableRow(tr('Breakdown by building type'),
                                       header=True))
        for t, v in buildings_by_type.iteritems():
            table_body.append(
                TableRow([t, int(v['flooded']), int(v['total'])])
            )

        impact_summary = Table(table_body).toNewlineFreeString()
        map_title = tr('Buildings inundated')

        style_classes = [dict(label=tr('Not Inundated'), value=0,
                              colour='#1EFC7C', transparency=0, size=0.5),
                         dict(label=tr('Inundated'), value=1,
                              colour='#F31A1C', transparency=0, size=0.5)]
        style_info = dict(target_field=target_field,
                          style_classes=style_classes,
                          style_type='categorizedSymbol')

        # Convert QgsVectorLayer to inasafe layer and return it
        building_layer = Vector(data=building_layer,
                   name=tr('Flooded buildings'),
                   keywords={'impact_summary': impact_summary,
                             'map_title': map_title,
                             'target_field': target_field},
                   style_info=style_info)
        return building_layer
