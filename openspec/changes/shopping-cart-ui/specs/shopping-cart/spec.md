## ADDED Requirements

### Requirement: Add to cart from product list
Each product row in the products table SHALL have an "Agregar al carrito" button. Clicking it adds the product with quantity 1 to the cart. If the product is already in the cart, it increments the quantity by 1 instead.

#### Scenario: Add a product to cart
- **WHEN** user clicks "Agregar al carrito" on a product not yet in the cart
- **THEN** the product SHALL be added to the cart with quantity 1

#### Scenario: Add duplicate product increments quantity
- **WHEN** user clicks "Agregar al carrito" on a product already in the cart
- **THEN** the quantity of that product SHALL increase by 1 (not create a duplicate entry)

#### Scenario: Button visible for all roles
- **WHEN** any authenticated user (CLIENT, PEDIDOS, STOCK, ADMIN) views the products table
- **THEN** each product row SHALL have the "Agregar al carrito" button

### Requirement: Cart page with product list
The `/carrito` page SHALL display all products in the cart with their quantities, unit prices, line totals, and a grand total.

#### Scenario: Cart shows all added products
- **WHEN** user navigates to `/carrito`
- **THEN** all products in the cart SHALL be displayed in a list/table

#### Scenario: Empty cart message
- **WHEN** the cart has no products and user navigates to `/carrito`
- **THEN** a message "El carrito está vacío" SHALL be displayed
- **THEN** a link/button to go back to products SHALL be shown

### Requirement: Quantity controls (minimum 1)
Each product in the cart SHALL have + and − buttons to adjust quantity. The minimum quantity is 1 — the − button SHALL be disabled or not decrease below 1.

#### Scenario: Increase quantity
- **WHEN** user clicks the + button for a product in the cart
- **THEN** the quantity SHALL increase by 1
- **THEN** the line total SHALL update accordingly

#### Scenario: Decrease quantity (above 1)
- **WHEN** user clicks the − button and current quantity is greater than 1
- **THEN** the quantity SHALL decrease by 1
- **THEN** the line total SHALL update accordingly

#### Scenario: Cannot decrease below 1
- **WHEN** user clicks the − button and current quantity is 1
- **THEN** the quantity SHALL remain at 1 (button does nothing or is disabled)

### Requirement: Remove product from cart
Each product in the cart SHALL have a "Quitar" or "Eliminar" button that removes the product entirely from the cart.

#### Scenario: Remove product
- **WHEN** user clicks "Quitar" on a product in the cart
- **THEN** the product SHALL be removed from the cart
- **THEN** the total SHALL update accordingly

### Requirement: Price calculation
The cart SHALL calculate and display the line total (precio × cantidad) for each product and the grand total of all products.

#### Scenario: Line total calculation
- **WHEN** viewing the cart
- **THEN** each product row SHALL display `precio × cantidad = total_linea`

#### Scenario: Grand total calculation
- **WHEN** viewing the cart
- **THEN** a total section SHALL display the sum of all line totals

### Requirement: Realizar pedido button
The cart SHALL have a "Realizar pedido" button. Its functionality SHALL be implemented in a future change — for now it can show a "Próximamente" message or simply be present.

#### Scenario: Button present
- **WHEN** the cart has at least one product
- **THEN** the "Realizar pedido" button SHALL be visible
- **WHEN** the cart is empty
- **THEN** the button SHALL be hidden or disabled

### Requirement: Cart persistence (localStorage)
The cart state SHALL persist in localStorage so it survives page reloads and navigation.

#### Scenario: Cart survives reload
- **WHEN** user adds products to cart, then reloads the page
- **THEN** the cart SHALL still contain those products

### Requirement: Landing page default
The application SHALL redirect to `/productos` by default (instead of `/categorias`) for all roles.

#### Scenario: Default redirect for admin
- **WHEN** an ADMIN user logs in and is redirected to `/`
- **THEN** the system SHALL redirect to `/productos`

#### Scenario: Cart link in navigation
- **WHEN** any authenticated user views the navigation bar
- **THEN** a "Carrito" link SHALL be visible with the count of items in the cart
