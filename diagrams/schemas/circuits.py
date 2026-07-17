"""
Pydantic schemas for Circuit diagram types.
"""
from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class ComponentType(str, Enum):
    RESISTOR = "resistor"
    CAPACITOR = "capacitor"
    INDUCTOR = "inductor"
    BATTERY = "battery"
    SWITCH = "switch"
    WIRE = "wire"
    GROUND = "ground"
    AMMETER = "ammeter"
    VOLTMETER = "voltmeter"
    LED = "led"
    BULB = "bulb"


class ComponentDirection(str, Enum):
    RIGHT = "right"
    LEFT = "left"
    UP = "up"
    DOWN = "down"


class CircuitComponent(BaseModel):
    type: ComponentType
    label: Optional[str] = None
    value: Optional[str] = None          # e.g. "10Ω", "100μF", "12V"
    direction: ComponentDirection = ComponentDirection.RIGHT
    length: float = Field(default=3.0, ge=1.0, le=10.0)
    reverse: bool = False                # reverse polarity for battery


class CircuitConnection(BaseModel):
    """Defines how to navigate: a sequence of segments that form the circuit."""
    components: List[CircuitComponent]
    topology: str = "series"    # series | parallel | bridge


# ── Resistor Network ──────────────────────────────────────────────────────────

class ResistorNode(BaseModel):
    label: str = ""
    resistors: List[str] = Field(default_factory=list)    # list of value strings, e.g. ["2Ω","3Ω"]


class ResistorNetworkSchema(BaseModel):
    topology: str = "series"     # series | parallel | series_parallel
    resistors: List[str] = Field(default_factory=list)    # ["R1=2Ω", "R2=3Ω", ...]
    voltage_source: Optional[str] = None                  # e.g. "12V"
    show_current: bool = True
    show_voltage: bool = True
    equivalent_label: bool = True

    @field_validator("resistors")
    @classmethod
    def at_least_one(cls, v):
        if not v:
            raise ValueError("At least one resistor is required")
        return v


# ── Capacitor Network ─────────────────────────────────────────────────────────

class CapacitorNetworkSchema(BaseModel):
    topology: str = "series"
    capacitors: List[str] = Field(default_factory=list)
    voltage_source: Optional[str] = None
    show_charge: bool = True

    @field_validator("capacitors")
    @classmethod
    def at_least_one(cls, v):
        if not v:
            raise ValueError("At least one capacitor is required")
        return v


# ── Basic DC Circuit ──────────────────────────────────────────────────────────

class BasicDCCircuitSchema(BaseModel):
    """A complete DC circuit defined as an ordered list of components."""
    components: List[CircuitComponent] = Field(default_factory=list)
    title: str = ""
    show_current_direction: bool = True
    show_labels: bool = True

    @field_validator("components")
    @classmethod
    def at_least_two(cls, v):
        if len(v) < 2:
            raise ValueError("Circuit requires at least 2 components")
        return v


# ── Logic Gates (digital electronics) ─────────────────────────────────────────

class GateType(str, Enum):
    AND = "AND"
    OR = "OR"
    NOT = "NOT"
    NAND = "NAND"
    NOR = "NOR"
    XOR = "XOR"
    XNOR = "XNOR"


class LogicGate(BaseModel):
    id: str
    gate_type: GateType
    label: Optional[str] = None

    @field_validator("gate_type", mode="before")
    @classmethod
    def normalise_gate_type(cls, v):
        if isinstance(v, str):
            v = v.strip().upper()
            allowed = {g.value for g in GateType}
            if v not in allowed:
                raise ValueError(
                    f"gate_type must be one of {sorted(allowed)}, got '{v}'")
        return v


class LogicInput(BaseModel):
    id: str
    label: str        # e.g. "A", "B"


class LogicConnection(BaseModel):
    from_id: str                                   # input id or gate id
    to_id: str                                     # gate id
    to_input_index: Optional[int] = Field(default=None, ge=0)


class LogicGatesSchema(BaseModel):
    """A combinational logic-gate network (inputs -> gates -> single output)."""
    gates: List[LogicGate]
    inputs: List[LogicInput]
    connections: List[LogicConnection]
    output_label: str = "Y"
    show_truth_table: bool = False
    title: str = ""

    @model_validator(mode="after")
    def check_network(self):
        if not self.gates:
            raise ValueError("At least one gate is required")
        if not self.inputs:
            raise ValueError("At least one input is required")

        input_ids = [i.id for i in self.inputs]
        gate_ids = [g.id for g in self.gates]
        all_ids = input_ids + gate_ids
        if len(set(all_ids)) != len(all_ids):
            raise ValueError("Input/gate ids must be unique")

        gate_id_set = set(gate_ids)
        id_set = set(all_ids)
        incoming = {gid: 0 for gid in gate_ids}
        for c in self.connections:
            if c.from_id not in id_set:
                raise ValueError(f"Connection from unknown id '{c.from_id}'")
            if c.to_id not in gate_id_set:
                raise ValueError(
                    f"Connection target '{c.to_id}' is not a gate id")
            incoming[c.to_id] += 1

        gate_type_by_id = {g.id: g.gate_type for g in self.gates}
        for gid, n in incoming.items():
            if gate_type_by_id[gid] == GateType.NOT:
                if n != 1:
                    raise ValueError(
                        f"NOT gate '{gid}' must have exactly 1 input, got {n}")
            elif n < 1:
                raise ValueError(f"Gate '{gid}' has no inputs wired to it")

        # Cycle check (Kahn's algorithm over gate->gate edges)
        deps = {gid: set() for gid in gate_ids}
        for c in self.connections:
            if c.from_id in gate_id_set:
                deps[c.to_id].add(c.from_id)
        resolved = set(input_ids)
        remaining = set(gate_ids)
        while remaining:
            ready = {g for g in remaining if deps[g] <= resolved}
            if not ready:
                raise ValueError("Gate network contains a cycle; "
                                 "only combinational (acyclic) circuits are supported")
            resolved |= ready
            remaining -= ready
        return self


# ── AC Phasor Diagram ─────────────────────────────────────────────────────────

class PhasorSpec(BaseModel):
    label: str                                     # e.g. "V_R", "V_L", "I"
    magnitude: float = Field(gt=0)
    angle_deg: float                               # measured CCW from +x axis


class ACCircuitType(str, Enum):
    SERIES_RLC = "series_rlc"
    RC = "rc"
    RL = "rl"
    LC = "lc"


class ACPhasorSchema(BaseModel):
    """Phasor (rotating-vector) diagram for AC circuits, e.g. series RLC."""
    phasors: List[PhasorSpec]
    show_resultant: bool = False
    show_angle_labels: bool = True
    reference_label: Optional[str] = None          # label on the +x reference axis
    circuit_type: Optional[ACCircuitType] = None   # draws a small companion circuit
    title: str = ""

    @field_validator("phasors")
    @classmethod
    def at_least_one_phasor(cls, v):
        if not v:
            raise ValueError("At least one phasor is required")
        return v


# ── Wheatstone Bridge family ──────────────────────────────────────────────────

class BridgeVariant(str, Enum):
    WHEATSTONE = "wheatstone"
    METRE_BRIDGE = "metre_bridge"
    POTENTIOMETER = "potentiometer"


class WheatstoneBridgeSchema(BaseModel):
    """Wheatstone bridge and its two lab incarnations (metre bridge, potentiometer).

    The balance condition is never taken from the params — the renderer computes it
    from the arm values / balance lengths given here.
    """
    variant: BridgeVariant = BridgeVariant.WHEATSTONE

    # -- wheatstone: the four diamond arms, in order P (A→B), Q (B→C), R (A→D), S (D→C)
    resistor_labels: List[str] = Field(default_factory=lambda: ["P", "Q", "R", "S"])
    resistor_values: List[Optional[str]] = Field(default_factory=list)   # "10Ω"; None/"" = unknown arm
    galvanometer_label: str = "G"
    cell_label: str = "E"
    show_balance_condition: bool = True
    show_current_arrows: bool = False

    # -- metre_bridge / potentiometer
    wire_length_cm: float = Field(default=100.0, gt=0)
    balance_length_cm: Optional[float] = Field(default=None, gt=0)
    unknown_label: str = "X"
    known_resistance: Optional[str] = None          # "10Ω" — the resistance box in the right gap

    # -- potentiometer: a second balance length turns it into an EMF comparison
    balance_length_2_cm: Optional[float] = Field(default=None, gt=0)
    emf_labels: List[str] = Field(default_factory=lambda: ["E1", "E2"])
    show_driver_cell: bool = True

    title: str = ""

    @field_validator("resistor_labels")
    @classmethod
    def four_arms(cls, v):
        if len(v) != 4:
            raise ValueError("resistor_labels must name exactly 4 arms (P, Q, R, S)")
        return v

    @model_validator(mode="after")
    def check_variant_params(self):
        if self.variant in (BridgeVariant.METRE_BRIDGE, BridgeVariant.POTENTIOMETER):
            if self.balance_length_cm is None:
                raise ValueError(
                    f"{self.variant.value} requires balance_length_cm "
                    "(the null point — the whole measurement)")
            for l in (self.balance_length_cm, self.balance_length_2_cm):
                if l is not None and l >= self.wire_length_cm:
                    raise ValueError(
                        f"balance length {l}cm must lie on the wire "
                        f"(0 < l < {self.wire_length_cm}cm)")
        if self.variant == BridgeVariant.METRE_BRIDGE and not self.known_resistance:
            raise ValueError("metre_bridge requires known_resistance to solve for the unknown")
        return self


# ── Rectifier ─────────────────────────────────────────────────────────────────

class RectifierType(str, Enum):
    HALF_WAVE = "half_wave"
    FULL_WAVE_CENTRE_TAP = "full_wave_centre_tap"
    FULL_WAVE_BRIDGE = "full_wave_bridge"


class RectifierSchema(BaseModel):
    """Diode rectifier + its input/output waveforms.

    The output waveform is derived from rectifier_type, so the circuit and the
    trace beneath it can never disagree.
    """
    rectifier_type: RectifierType = RectifierType.HALF_WAVE
    show_transformer: bool = True
    show_diodes: bool = True                       # False leaves the diode slots empty
    load_label: str = "R_L"
    show_input_waveform: bool = True
    show_output_waveform: bool = True
    show_filter_capacitor: bool = False
    filter_capacitor_label: str = "C"
    input_label: str = "AC input"
    title: str = ""

    @model_validator(mode="after")
    def centre_tap_needs_transformer(self):
        # A centre tap is a tapping *of the secondary winding*; without the
        # transformer the topology does not exist.
        if self.rectifier_type == RectifierType.FULL_WAVE_CENTRE_TAP:
            self.show_transformer = True
        return self


# ── AC RLC Circuit ────────────────────────────────────────────────────────────

class RLCTopology(str, Enum):
    SERIES = "series"
    PARALLEL = "parallel"


class RLCComponentType(str, Enum):
    RESISTOR = "resistor"
    INDUCTOR = "inductor"
    CAPACITOR = "capacitor"


class RLCComponent(BaseModel):
    type: RLCComponentType
    label: Optional[str] = None
    value: Optional[str] = None     # "100Ω", "1mH", "1µF" — SI prefixes are parsed for f₀


class RLCCircuitSchema(BaseModel):
    """Series or parallel R-L-C driven by an AC source."""
    topology: RLCTopology = RLCTopology.SERIES
    components: List[RLCComponent]
    source_label: str = "V = V0 sin ωt"
    show_ac_source: bool = True
    show_impedance_formula: bool = False
    show_resonance: bool = False
    show_current_direction: bool = True
    title: str = ""

    @field_validator("components")
    @classmethod
    def distinct_rlc(cls, v):
        if not v:
            raise ValueError("At least one of R, L, C is required")
        types = [c.type for c in v]
        if len(set(types)) != len(types):
            raise ValueError("Each of R, L, C may appear at most once")
        return v


# ── Mesh / multi-loop network (Kirchhoff) ─────────────────────────────────────

class MeshComponentType(str, Enum):
    RESISTOR = "resistor"
    BATTERY = "battery"
    CAPACITOR = "capacitor"
    INDUCTOR = "inductor"
    AMMETER = "ammeter"
    VOLTMETER = "voltmeter"
    GALVANOMETER = "galvanometer"
    SWITCH = "switch"


class Polarity(str, Enum):
    """Orientation of a polarised component along its branch (from_node → to_node)."""
    FORWARD = "forward"      # + terminal faces to_node
    REVERSE = "reverse"      # + terminal faces from_node


class CurrentDirection(str, Enum):
    FORWARD = "forward"      # from_node → to_node
    REVERSE = "reverse"      # to_node → from_node


class LoopDirection(str, Enum):
    CW = "cw"
    CCW = "ccw"


class MeshNode(BaseModel):
    id: str
    x: float
    y: float
    label: Optional[str] = None


class MeshComponent(BaseModel):
    type: MeshComponentType
    label: Optional[str] = None
    value: Optional[str] = None            # "10Ω", "12V", "100µF"
    polarity: Polarity = Polarity.FORWARD


class MeshBranch(BaseModel):
    from_node: str
    to_node: str
    components: List[MeshComponent] = Field(default_factory=list)
    current_label: Optional[str] = None    # "I1", "I2" …
    current_direction: CurrentDirection = CurrentDirection.FORWARD


class MeshLoop(BaseModel):
    node_ids: List[str]                    # the cycle, in order; the closing edge is implied
    label: str = "Loop 1"
    direction: LoopDirection = LoopDirection.CW


class MeshCircuitSchema(BaseModel):
    """A general multi-loop network: nodes at fixed coordinates, branches between them.

    Unlike basic_dc_circuit (an ordered list = one loop), this expresses an
    arbitrary graph, which is what every Kirchhoff's-laws question needs.
    """
    nodes: List[MeshNode]
    branches: List[MeshBranch]
    loops: List[MeshLoop] = Field(default_factory=list)
    show_node_labels: bool = True
    show_currents: bool = True
    show_kvl_loops: bool = True
    title: str = ""

    @model_validator(mode="after")
    def check_network(self):
        if len(self.nodes) < 2:
            raise ValueError("A network needs at least 2 nodes")
        ids = [n.id for n in self.nodes]
        if len(set(ids)) != len(ids):
            raise ValueError("Node ids must be unique")
        known = set(ids)

        if not self.branches:
            raise ValueError("A network needs at least 1 branch")

        degree = {i: 0 for i in ids}
        adjacency: dict = {}
        for b in self.branches:
            if b.from_node not in known:
                raise ValueError(f"Branch references unknown node '{b.from_node}'")
            if b.to_node not in known:
                raise ValueError(f"Branch references unknown node '{b.to_node}'")
            if b.from_node == b.to_node:
                raise ValueError(
                    f"Branch from '{b.from_node}' to itself is a short, not a branch")
            degree[b.from_node] += 1
            degree[b.to_node] += 1
            key = tuple(sorted((b.from_node, b.to_node)))
            adjacency[key] = adjacency.get(key, 0) + 1

        # A node with one branch is a dead end: no current can flow through it, so
        # the picture would show a circuit that cannot exist.
        dangling = sorted(i for i in ids if degree[i] < 2)
        if dangling:
            raise ValueError(
                f"Dangling node(s) {dangling}: every node needs at least 2 branches "
                "for current to flow through it")

        for loop in self.loops:
            n = len(loop.node_ids)
            if n < 2:
                raise ValueError(
                    f"Loop '{loop.label}' needs at least 2 nodes to close a cycle")
            if len(set(loop.node_ids)) != n:
                raise ValueError(
                    f"Loop '{loop.label}' repeats a node; a mesh visits each node once")
            for nid in loop.node_ids:
                if nid not in known:
                    raise ValueError(
                        f"Loop '{loop.label}' references unknown node '{nid}'")
            if n == 2:
                # Two nodes only close a loop when two distinct branches join them.
                key = tuple(sorted(loop.node_ids))
                if adjacency.get(key, 0) < 2:
                    raise ValueError(
                        f"Loop '{loop.label}' is not a cycle: nodes "
                        f"{loop.node_ids} are joined by fewer than 2 branches")
            else:
                for k in range(n):
                    a, b = loop.node_ids[k], loop.node_ids[(k + 1) % n]
                    if adjacency.get(tuple(sorted((a, b))), 0) < 1:
                        raise ValueError(
                            f"Loop '{loop.label}' is not a cycle: no branch "
                            f"between '{a}' and '{b}'")
        return self


# ── Transistor Amplifier ──────────────────────────────────────────────────────

class AmplifierConfiguration(str, Enum):
    COMMON_EMITTER = "common_emitter"
    COMMON_BASE = "common_base"
    COMMON_COLLECTOR = "common_collector"


class TransistorType(str, Enum):
    NPN = "npn"
    PNP = "pnp"


class TransistorAmplifierSchema(BaseModel):
    """Single-stage BJT amplifier.

    The phase relation between Vin and Vout is derived from `configuration`, never
    taken from the params: only the common-emitter stage inverts (180°).
    """
    configuration: AmplifierConfiguration = AmplifierConfiguration.COMMON_EMITTER
    transistor_type: TransistorType = TransistorType.NPN
    show_biasing_resistors: bool = True
    show_coupling_capacitors: bool = True
    show_supply: bool = True
    show_input_output: bool = True
    show_waveforms: bool = False
    supply_label: str = "Vcc"
    title: str = ""


# ── Transformer ───────────────────────────────────────────────────────────────

class TransformerKind(str, Enum):
    STEP_UP = "step_up"
    STEP_DOWN = "step_down"


class TransformerSchema(BaseModel):
    """Ideal (or given-efficiency) transformer.

    Ns/Np = Vs/Vp = Ip/Is. Whatever is missing is computed; whatever is supplied
    inconsistently is recomputed, with the turns ratio winning.
    """
    transformer_type: TransformerKind = TransformerKind.STEP_DOWN
    primary_turns: Optional[float] = Field(default=None, gt=0)
    secondary_turns: Optional[float] = Field(default=None, gt=0)
    primary_voltage: Optional[str] = None        # "220V" / 220
    secondary_voltage: Optional[str] = None
    primary_current: Optional[str] = None        # "2A"
    secondary_current: Optional[str] = None
    show_core: bool = True
    show_turns_ratio: bool = True
    show_flux_direction: bool = False
    show_equations: bool = False
    efficiency: Optional[float] = Field(default=None, gt=0, le=100)   # percent
    title: str = ""

    @field_validator("primary_voltage", "secondary_voltage",
                     "primary_current", "secondary_current", mode="before")
    @classmethod
    def stringify(cls, v):
        return None if v is None else str(v)


# ── RC Circuit (charge / discharge) ───────────────────────────────────────────

class RCMode(str, Enum):
    CHARGING = "charging"
    DISCHARGING = "discharging"
    BOTH = "both"


class RCGraphQuantity(str, Enum):
    VOLTAGE = "voltage"
    CHARGE = "charge"
    CURRENT = "current"


class RCCircuitSchema(BaseModel):
    """Series RC driven by a DC emf through a key.

    tau = RC is computed, never read from the params, and the graph shape follows
    from (mode, graph_quantity): the CURRENT decays exponentially while charging
    *and* while discharging — only V and Q rise on charge.
    """
    mode: RCMode = RCMode.CHARGING
    resistance: Optional[str] = "1kΩ"
    capacitance: Optional[str] = "100µF"
    emf: Optional[str] = "10V"
    show_switch: bool = True
    show_time_constant: bool = True
    show_graph: bool = True
    graph_quantity: RCGraphQuantity = RCGraphQuantity.VOLTAGE
    mark_time_constants: bool = False
    title: str = ""

    @field_validator("resistance", "capacitance", "emf", mode="before")
    @classmethod
    def stringify(cls, v):
        return None if v is None else str(v)


# ── Galvanometer conversion (ammeter / voltmeter) ─────────────────────────────

class GalvanometerConversionType(str, Enum):
    TO_AMMETER = "to_ammeter"
    TO_VOLTMETER = "to_voltmeter"
    NONE = "none"


class GalvanometerConversionSchema(BaseModel):
    """Converting a galvanometer into an ammeter (shunt in PARALLEL) or a
    voltmeter (high resistance in SERIES).

    The required resistance is computed here; a shunt drawn in series (or a
    multiplier drawn in parallel) is a different instrument entirely.
    """
    conversion: GalvanometerConversionType = GalvanometerConversionType.TO_AMMETER
    galvanometer_resistance: Optional[str] = None     # G, e.g. "100Ω"
    full_scale_current: Optional[str] = None          # Ig, e.g. "1mA"
    target_range: Optional[str] = None                # "5A" (ammeter) / "15V" (voltmeter)
    show_shunt: bool = True
    show_series_resistance: bool = True
    show_formula: bool = True
    title: str = ""

    @field_validator("galvanometer_resistance", "full_scale_current",
                     "target_range", mode="before")
    @classmethod
    def stringify(cls, v):
        return None if v is None else str(v)


# ── Electromagnetic machine (generator / motor) ───────────────────────────────

class EMMachineType(str, Enum):
    AC_GENERATOR = "ac_generator"
    DC_GENERATOR = "dc_generator"
    DC_MOTOR = "dc_motor"


class RotationSense(str, Enum):
    CW = "clockwise"
    CCW = "anticlockwise"


class EMMachineSchema(BaseModel):
    """A rotating-coil machine in a magnetic field: AC generator, DC generator or
    DC motor.

    The single fact that separates the three is the ring type, and it is derived
    from `machine`, never taken from the params: an AC generator uses two full
    SLIP RINGS, while a DC generator/motor uses a SPLIT-RING commutator (the split
    is what reverses the external connection every half turn — rectifying the
    output of a DC generator and keeping a motor's torque one-way). The output
    waveform (AC → sinusoid, DC generator → rectified humps) follows the same fact.
    """
    machine: EMMachineType = EMMachineType.AC_GENERATOR
    show_flux: bool = True
    show_brushes: bool = True
    show_output_waveform: bool = True
    show_force_directions: bool = False
    rotation: RotationSense = RotationSense.CW
    title: str = ""


# ── Combinational logic (multi-gate, multi-output) ────────────────────────────

class CombinationalCircuit(str, Enum):
    HALF_ADDER = "half_adder"
    FULL_ADDER = "full_adder"
    HALF_SUBTRACTOR = "half_subtractor"
    MUX_2TO1 = "mux_2to1"
    SR_LATCH = "sr_latch"
    NETLIST = "netlist"


class LogicOutput(BaseModel):
    id: str                # the gate id whose output this is
    label: str             # e.g. "Sum", "Carry"


class LogicCombinationalSchema(BaseModel):
    """A named combinational building block, or a general gate netlist.

    The truth table is COMPUTED by evaluating the actual gate netlist for every
    input combination — never hand-written — so the drawing and the table cannot
    disagree. (sr_latch is the one feedback circuit here; its table is found by
    settling the cross-coupled NOR equations to steady state.)
    """
    circuit: CombinationalCircuit = CombinationalCircuit.HALF_ADDER
    # -- only for circuit == "netlist"
    gates: List[LogicGate] = Field(default_factory=list)
    inputs: List[LogicInput] = Field(default_factory=list)
    connections: List[LogicConnection] = Field(default_factory=list)
    outputs: List[LogicOutput] = Field(default_factory=list)
    # --
    show_truth_table: bool = True
    output_labels: Optional[List[str]] = None      # override the derived output names
    title: str = ""

    @model_validator(mode="after")
    def check_netlist(self):
        if self.circuit == CombinationalCircuit.NETLIST:
            if not self.gates:
                raise ValueError("netlist circuit requires at least one gate")
            if not self.inputs:
                raise ValueError("netlist circuit requires at least one input")
            if not self.outputs:
                raise ValueError("netlist circuit requires at least one output")
            gate_ids = {g.id for g in self.gates}
            for o in self.outputs:
                if o.id not in gate_ids:
                    raise ValueError(
                        f"output '{o.label}' names unknown gate id '{o.id}'")
        return self


# ── Zener voltage regulator ───────────────────────────────────────────────────

class ZenerRegulatorSchema(BaseModel):
    """A shunt Zener regulator: unregulated Vin, series resistance Rs, and the
    Zener in REVERSE bias across the load.

    The Zener works in breakdown, so its cathode is the positive terminal (the
    bent-cathode symbol points that way). The regulated output is derived: Vout is
    clamped to Vz for as long as Vin exceeds Vz — that clamping IS the point, so it
    is computed from Vz, never taken from the params.
    """
    zener_voltage: str = "5.1V"
    series_resistance: str = "1kΩ"
    input_voltage: Optional[str] = "10V"
    load_label: str = "R_L"
    show_load: bool = True
    show_waveforms: bool = True
    show_current_labels: bool = True
    title: str = ""

    @field_validator("zener_voltage", "series_resistance",
                     "input_voltage", mode="before")
    @classmethod
    def stringify(cls, v):
        return None if v is None else str(v)


# ── Transistor switch (cutoff / saturation) ───────────────────────────────────

class SwitchState(str, Enum):
    ON = "on"
    OFF = "off"
    BOTH = "both"


class SwitchLoadType(str, Enum):
    LAMP = "lamp"
    LED = "led"
    RELAY = "relay"
    MOTOR = "motor"


class TransistorSwitchSchema(BaseModel):
    """A BJT used as a switch (not an amplifier): a base resistor RB drives the
    transistor between cutoff (OFF, load de-energised) and saturation (ON, load
    energised).

    Which state lights the load is derived from the drive, never asserted: at
    cutoff Ic ≈ 0 and Vce ≈ Vcc; at saturation Vce ≈ 0 and Ic ≈ Vcc/R_load. The
    load line and its two operating points are computed from Vcc and R_load.
    """
    transistor_type: TransistorType = TransistorType.NPN
    state: SwitchState = SwitchState.BOTH
    load_type: SwitchLoadType = SwitchLoadType.LAMP
    show_regions: bool = True
    supply_label: str = "Vcc"
    base_resistor_label: str = "RB"
    title: str = ""


# ── Cathode-ray oscilloscope (CRO) ────────────────────────────────────────────

class ScreenWaveform(str, Enum):
    SINE = "sine"
    SQUARE = "square"
    DC = "dc"
    LISSAJOUS = "lissajous"


class CROSchema(BaseModel):
    """Cathode-ray oscilloscope: electron gun (cathode, control grid, accelerating
    anodes), the two deflection-plate pairs (Y then X), and the fluorescent screen
    with a trace on it.

    When the trace is a Lissajous figure it is COMPUTED from the frequency ratio
    (x = sin(fx·t + φ), y = sin(fy·t)); the number of lobes therefore follows from
    the ratio and is never taken from the params.
    """
    show_electron_beam: bool = True
    screen_waveform: ScreenWaveform = ScreenWaveform.SINE
    show_labels: bool = True
    timebase: bool = True
    lissajous_ratio: str = "1:2"           # fx:fy
    lissajous_phase_deg: float = 90.0
    title: str = ""

    @field_validator("lissajous_ratio", mode="before")
    @classmethod
    def stringify_ratio(cls, v):
        return "1:2" if v is None else str(v)
