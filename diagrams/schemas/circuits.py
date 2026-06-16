"""
Pydantic schemas for Circuit diagram types.
"""
from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


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
