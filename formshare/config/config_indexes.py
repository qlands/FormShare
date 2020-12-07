from formshare.config.elasticfeeds import configure_manager
from formshare.processes.elasticsearch.user_index import configure_user_index_manager


def configure_indexes(settings):
    # Load the feeds manager
    configure_manager(settings)

    # Load the user index manager
    configure_user_index_manager(settings)