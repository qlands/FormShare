from formshare.products import create_product, add_metadata_to_product


def register_products():
    products = []
    # A new product
    new_product = create_product('fs1import', False, "fas fa-file-import")
    add_metadata_to_product(new_product, 'author', 'QLands Technology Consultants')
    add_metadata_to_product(new_product, 'version', '1.0')
    add_metadata_to_product(new_product, 'Licence', 'LGPL')
    products.append(new_product)

    new_product = create_product('repository', False, "fas fa-database")
    add_metadata_to_product(new_product, 'author', 'QLands Technology Consultants')
    add_metadata_to_product(new_product, 'version', '1.0')
    add_metadata_to_product(new_product, 'Licence', 'LGPL')
    products.append(new_product)

    new_product = create_product('xlsx_export', False, "far fa-file-excel")
    add_metadata_to_product(new_product, 'author', 'QLands Technology Consultants')
    add_metadata_to_product(new_product, 'version', '1.0')
    add_metadata_to_product(new_product, 'Licence', 'LGPL')
    products.append(new_product)

    new_product = create_product('media_export', False, "far fa-images")
    add_metadata_to_product(new_product, 'author', 'QLands Technology Consultants')
    add_metadata_to_product(new_product, 'version', '1.0')
    add_metadata_to_product(new_product, 'Licence', 'LGPL')
    products.append(new_product)

    return products
