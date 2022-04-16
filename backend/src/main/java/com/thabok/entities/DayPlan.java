package com.thabok.entities;

import java.util.ArrayList;
import java.util.List;
import java.util.stream.Collectors;

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
    	List<PartyTouple> partyTouplesSorted = partyTouples.stream()
    			.sorted((pt1, pt2) -> pt1.getDriver().toString().compareTo(pt2.getDriver().toString()))
    			.collect(Collectors.toList());
    	for (PartyTouple partyTouple : partyTouplesSorted) {
			s += "\t- " + (partyTouple.isDesignatedDriver() ? "* " : "  ") +  String.join("\n\t    ", partyTouple.toString().split("\\n")) + "\n";
		}
    	return s;
    }
}
