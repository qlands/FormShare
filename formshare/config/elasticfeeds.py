from elasticfeeds.manager import Manager


def configure_manager(settings):
    try:
        host = settings['elasticsearch.host']
    except KeyError:
        host = "localhost"

    try:
        port = int(settings['elasticsearch.port'])
    except KeyError:
        port = 9200

    try:
        feed_index = settings['elasticsearch.feed_index']
    except KeyError:
        feed_index = 'formshare_feeds'

    try:
        network_index = settings['elasticsearch.network_index']
    except KeyError:
        network_index = 'formshare_network'

    try:
        url_prefix = settings['elasticsearch.url_prefix']
    except KeyError:
        url_prefix = None

    try:
        use_ssl = settings['elasticsearch.use_ssl']
        if use_ssl == 'True':
            use_ssl = True
        else:
            use_ssl = False
    except KeyError:
        use_ssl = False

    try:
        number_of_shards_in_feeds = int(settings['elasticsearch.number_of_shards_in_feeds'])
    except KeyError:
        number_of_shards_in_feeds = 5

    try:
        number_of_replicas_in_feeds = int(settings['elasticsearch.number_of_replicas_in_feeds'])
    except KeyError:
        number_of_replicas_in_feeds = 1

    try:
        number_of_shards_in_network = int(settings['elasticsearch.number_of_shards_in_network'])
    except KeyError:
        number_of_shards_in_network = 5

    try:
        number_of_replicas_in_network = int(settings['elasticsearch.number_of_replicas_in_network'])
    except KeyError:
        number_of_replicas_in_network = 5

    try:
        max_link_size = int(settings['elasticsearch.max_link_size'])
    except KeyError:
        max_link_size = 10000

    feeds_manager = Manager(feed_index, network_index, host, port, url_prefix, use_ssl, number_of_shards_in_feeds,
                            number_of_replicas_in_feeds, number_of_shards_in_network, number_of_replicas_in_network,
                            False, False, max_link_size)
    return feeds_manager


def get_manager(request):
    feeds_manager = configure_manager(request.registry.settings)
    return feeds_manager
