## ADDED Requirements

### Requirement: Tree table renders hierarchical categories
The system SHALL render categories as an expandable tree table where each row shows a category with visual indentation indicating its depth level. Root categories appear at the top level, children are indented below their parent.

#### Scenario: Tree loads from backend endpoint
- **WHEN** the CategoriasCRUD page loads
- **THEN** the system SHALL call `GET /categorias/tree` to obtain the nested category structure
- **THEN** the tree table SHALL render root categories at indent level 0

#### Scenario: Child categories are indented under parent
- **WHEN** a category has `subcategorias` in the API response
- **THEN** each child SHALL be rendered as a row indented below its parent using padding/margin proportional to its depth (e.g., `pl-{depth*4}` Tailwind class)

#### Scenario: Tree supports N levels of nesting
- **WHEN** a grandchild category exists (child of a child)
- **THEN** the system SHALL render it at depth level 2 (or deeper), indented further than its parent

### Requirement: Expand/collapse behavior
Each category that has children SHALL display an expand/collapse toggle icon. Clicking it toggles the visibility of its direct children.

#### Scenario: Expand a category with children
- **WHEN** user clicks the expand icon (+) on a category that has children
- **THEN** its direct children SHALL become visible
- **THEN** the icon SHALL change to collapse (−)

#### Scenario: Collapse a category
- **WHEN** user clicks the collapse icon (−) on an expanded category
- **THEN** its children SHALL be hidden
- **THEN** the icon SHALL change to expand (+)

#### Scenario: Categories without children show no toggle
- **WHEN** a category has no `subcategorias`
- **THEN** the expand/collapse area SHALL be empty or show a non-clickable placeholder

### Requirement: CRUD operations on tree
The system SHALL preserve all existing CRUD operations (create, edit, delete) on the tree structure. After any mutation, the tree SHALL be refreshed from the backend.

#### Scenario: Create category refreshes tree
- **WHEN** a user creates a new category via the form
- **THEN** the system SHALL call `GET /categorias/tree` to reload the full tree
- **THEN** the new category SHALL appear in its correct hierarchical position

#### Scenario: Edit category refreshes tree
- **WHEN** a user updates a category (including changing its parent)
- **THEN** the tree SHALL be reloaded and the category SHALL appear under its new parent

#### Scenario: Delete category refreshes tree
- **WHEN** a user deletes a category
- **THEN** the tree SHALL be reloaded and the deleted category SHALL no longer appear

### Requirement: Filter by name preserves tree context
When filtering by name, the system SHALL show matching categories AND their ancestors (to preserve tree context).

#### Scenario: Filter matches a child category
- **WHEN** a user types a filter string that matches a child category name
- **THEN** the tree SHALL show that child AND all its ancestor categories up to the root
- **THEN** categories that do not match and have no matching descendants SHALL be hidden

#### Scenario: Filter with no matches
- **WHEN** a user types a filter string that matches no category
- **THEN** the tree table SHALL display "Sin resultados" message

### Requirement: ParentSelector shows hierarchical list
When selecting a parent category during create/edit, the ParentSelector popup SHALL display categories in tree order with indentation.

#### Scenario: ParentSelector shows tree
- **WHEN** a user opens the ParentSelector popup
- **THEN** categories SHALL be listed in tree order with indentation by depth level
- **THEN** a category cannot be its own parent or descendant

### Requirement: SubcategoriasPopup is removed
The system SHALL NOT use the `SubcategoriasPopup` modal component. Subcategories are visible inline in the tree table.

#### Scenario: No SubcategoriasPopup rendered
- **WHEN** the CategoriasCRUD page renders
- **THEN** the `SubcategoriasPopup` component SHALL NOT appear
- **THEN** all subcategories SHALL be visible via expand/collapse in the tree table

### Requirement: Export works with tree data
The export to Excel functionality SHALL continue to work, exporting a flat representation of the tree (including depth information).

#### Scenario: Export preserves flat structure
- **WHEN** a user clicks "Exportar Excel"
- **THEN** the system SHALL export the visible categories (including filtered ones) as a flat list
- **THEN** each row SHALL include its depth level
