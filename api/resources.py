from tastypie.resources import ModelResource, ALL
from tastypie import fields

from bostonparks.tastyhacks import EncodedGeoResource
from parkmap.models import Neighborhood, Activity, Facility, Park, Parktype


class ParkResource(EncodedGeoResource):
    """
    Park
    """
    class Meta:
        queryset = Park.objects.transform(4326).all()
        allowed_methods = ['get', ]
        filtering = {
            'name': ALL,
        }


class ExploreActivityResource(ModelResource):
    class Meta:
        queryset = Activity.objects.all()
        allowed_methods = ('get',)
        excludes = ('status', 'location')

    def build_filters(self, filters=None):
        if filters is None:
            filters = {}

        orm_filters = super(ExploreActivityResource, self).build_filters(filters)
        if "neighborhood" in filters and \
           "parktype" in filters:
            activities = filter_explore_activity(filters)
            orm_filters = {"pk__in": [i.id for i in activities]}
        return orm_filters


class ExploreParkResource(ModelResource):
    class Meta:
        queryset = Park.objects.all()
        allowed_methods = ('get',)
        excludes = ('status', 'location')

    def build_filters(self, filters=None):
        if filters is None:
            filters = {}

        orm_filters = super(ExploreParkResource, self).build_filters(filters)
        if "neighborhood" in filters and \
           "parktype" in filters and \
           "activity_ids" in filters:
            parks = filter_explore_park(filters)
            orm_filters = {"pk__in": [i.os_id for i in parks]}
        return orm_filters


class ExploreFacilityResource(ModelResource):
    class Meta:
        queryset = Facility.objects.all()
        allowed_methods = ('get',)
        excludes = ('status', 'location')

    def build_filters(self, filters=None):
        if filters is None:
            filters = {}

        orm_filters = super(ExploreFacilityResource, self).build_filters(filters)
        if "neighborhood" in filters and \
           "parktype" in filters and \
           "activity_ids" in filters:
            facilities = filter_explore_facility(filters)
            orm_filters = {"pk__in": [i.id for i in facilities]}
        return orm_filters


class NeighborhoodResource(ModelResource):
    class Meta:
        queryset = Neighborhood.objects.all()
        allowed_methods = ['get']
        excludes = ['geometry', 'objects']

    def build_filters(self, filters=None):
        if filters is None:
            filters = {}
        orm_filters = super(NeighborhoodResource, self).build_filters(filters)
        if  "activity" in filters:
            neighborhoods = get_neighborhoods(filters['activity'])
            queryset = Neighborhood.objects.filter(pk__in=neighborhoods)
            orm_filters = {"pk__in": [i.id for i in queryset]}
        return orm_filters


class ParktypeResource(ModelResource):
    class Meta:
        queryset = Parktype.objects.all()
        allowed_methods = ['get']

    def build_filters(self, filters=None):
        if filters is None:
            filters = {}
        orm_filters = super(ParktypeResource, self).build_filters(filters)
        if  "neighborhood" in filters:
            parktypes = get_parktypes(filters['neighborhood'])
            queryset = Parktype.objects.filter(pk__in=parktypes)
            orm_filters = {"pk__in": [i.id for i in queryset]}
        return orm_filters


class ActivityResource(ModelResource):
    class Meta:
        queryset = Activity.objects.all()
        allowed_methods = ['get']

    def build_filters(self, filters=None):
        if filters is None:
            filters = {}
        orm_filters = super(ActivityResource, self).build_filters(filters)
        if  "neighborhood" in filters:
            activities = get_activities(filters['neighborhood'])
            queryset = Activity.objects.filter(pk__in=activities)
            orm_filters = {"pk__in": [i.id for i in queryset]}
        return orm_filters


class EntryResource(ModelResource):
    neighborhood = fields.ForeignKey(NeighborhoodResource, 'neighborhood')
    activity = fields.ForeignKey(ActivityResource, 'activity')
    parktype = fields.ForeignKey(ParktypeResource, 'parktype')
    explorepark = fields.ForeignKey(ExploreParkResource, 'explorepark')
    explorefacility = fields.ForeignKey(ExploreFacilityResource, 'explorefacility')
    exploreactivity = fields.ForeignKey(ExploreActivityResource, 'exploreactivity')

    class Meta:
        queryset = Neighborhood.objects.all()
        allowed_methods = ['get']

## Indepth filter functions
def get_neighborhoods(activity_slug):
    """
    Get all Neighborhood ids that have an activity.
    """
    activity = Activity.objects.get(slug=activity_slug)
    parks = [fac.park for fac in Facility.objects.filter(activity=activity) if fac.park]
    neighborhoods = []
    for p in parks:
        neighborhoods.extend(p.neighborhoods.all())
    return list(set([n.id for n in neighborhoods]))


def get_parktypes(neighborhood_slug):
    """
    Get all Neighborhood ids that have an activity.
    """
    neighborhood = Neighborhood.objects.get(slug=neighborhood_slug)
    parks = Park.objects.filter(neighborhoods=neighborhood)
    parktypes = []
    for park in parks:
        parktypes.append(park.parktype.id)
    return list(set(parktypes))


def get_activities(neighborhood_slug):
    """
    Get all activitty ids that are in a neighborhood.
    """
    neighborhood = Neighborhood.objects.get(slug=neighborhood_slug)
    parks = Park.objects.filter(geometry__intersects=neighborhood.geometry)
    facilities = []
    for park in parks:
        facilities.extend(park.facility_set.all())
    activities = []
    for fac in facilities:
        activities.extend(fac.activity.all())
    return list(set([a.id for a in activities]))


def filter_explore_park(filters):
    neighborhood = Neighborhood.objects.get(slug=filters['neighborhood'])
    parktype = Parktype.objects.get(pk=filters['parktype'])
    activity_pks = filters['activity_ids'].split(",")
    activities = Activity.objects.filter(pk__in=activity_pks)
    parks = Park.objects.filter(neighborhoods=neighborhood, parktype=parktype)
    facilities = Facility.objects.filter(park__in=parks)
    parks_filtered = []
    for facility in facilities:
        for activity in activities:
            if activity in facility.activity.all():
                parks_filtered.append(facility.park)
    return parks_filtered


def filter_explore_activity(filters):
    neighborhood = Neighborhood.objects.get(slug=filters['neighborhood'])
    parktype = Parktype.objects.get(pk=filters['parktype'])
    parks = Park.objects.filter(neighborhoods=neighborhood, parktype=parktype)
    facilities = Facility.objects.filter(park__in=parks)
    activities = []
    for facility in facilities:
        activities.extend(facility.activity.all())
    return list(set(activities))


def filter_explore_facility(filters):
    neighborhood = Neighborhood.objects.get(slug=filters['neighborhood'])
    parktype = Parktype.objects.get(pk=filters['parktype'])
    activity_pks = filters['activity_ids'].split(",")
    activities = Activity.objects.filter(pk__in=activity_pks)
    parks = Park.objects.filter(neighborhoods=neighborhood, parktype=parktype)
    facilities = Facility.objects.filter(park__in=parks)
    facilities_filtered = []
    for facility in facilities:
        for activity in activities:
            if activity in facility.activity.all():
                facilities_filtered.append(facility)
    return facilities_filtered
