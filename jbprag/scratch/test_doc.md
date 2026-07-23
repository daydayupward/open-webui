# Main Section

This is a paragraph under the main section of our physical design guide.
It describes the overall placement steps.

## Subsection A: Placement Steps

Here are the detailed steps for cell placement in the design:
1. Import target Netlist.
2. Initialize floorplan coordinates and bounds.
3. Run global placement optimizing for WNS and wire length.
4. Insert decoupling capacitors.

Below is the diagram illustrating the cell placement flow:
![Placement Flowchart](/static/uploads/images/test_flowchart.png "Placement Flow")

Ensure all physical cells are colocated correctly to avoid routing congestion.

## Subsection B: Routing Steps

Here are the routing steps:
1. Run clock tree synthesis (CTS) using clockDesign.
2. Run global routing.
3. Run detail routing.
