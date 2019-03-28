from formshare.products import create_product, add_metadata_to_product


def register_products():
    products = []
    # A new product
    new_product = create_product('fs1import')
    add_metadata_to_product(new_product, 'author', 'QLands Technology Consultants')
    add_metadata_to_product(new_product, 'version', '1.0')
    add_metadata_to_product(new_product, 'Licence', 'LGPL')
    products.append(new_product)

    new_product = create_product('repository')
    add_metadata_to_product(new_product, 'author', 'QLands Technology Consultants')
    add_metadata_to_product(new_product, 'version', '1.0')
    add_metadata_to_product(new_product, 'Licence', 'LGPL')
    products.append(new_product)

    return products
