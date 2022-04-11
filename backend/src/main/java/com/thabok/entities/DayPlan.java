package com.thabok.entities;

import java.util.ArrayList;
import java.util.List;

public class DayPlan {

	public boolean passengersBalanced = false;
	private DayOfWeekABCombo dayOfWeekABCombo;
	private List<PartyTouple> partyTouples = new ArrayList<>();
	
	public DayPlan() {
	}
	public DayPlan(DayOfWeekABCombo combo) {
		this.dayOfWeekABCombo = combo;
	}
	public DayOfWeekABCombo getDayOfWeekABCombo() {
		return dayOfWeekABCombo;
	}
	public void setDayOfWeekABCombo(DayOfWeekABCombo dayOfWeekABCombo) {
		this.dayOfWeekABCombo = dayOfWeekABCombo;
	}
	public List<PartyTouple> getPartyTouples() {
		return partyTouples;
	}
	public void setPartyTouples(List<PartyTouple> partyTouples) {
		this.partyTouples = partyTouples;
	}
	public void addPartyTouple(PartyTouple partyTouple) {
		this.partyTouples.add(partyTouple);
	}
	
	public boolean isWeekA() {
		return this.dayOfWeekABCombo.isWeekA();
	}
	
    public String toString() {
    	String s = "[" + dayOfWeekABCombo + "]\n";
    	for (PartyTouple partyTouple : partyTouples) {
			s += "\t- " + (partyTouple.isDesignatedDriver() ? "* " : "  ") +  String.join("\n\t    ", partyTouple.toString().split("\\n")) + "\n";
		}
    	return s;
    }
}
