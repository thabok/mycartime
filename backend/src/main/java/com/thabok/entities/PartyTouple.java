package com.thabok.entities;

import java.util.HashSet;
import java.util.Set;

public class PartyTouple {

	private Party partyThere;
	private Party partyBack;
	private boolean isDesignatedDriver;
	
	/**
	 * This list contains all persons that have the same schedule as the driver for this day.
	 */
	private Set<Person> possibleDrivers = new HashSet<>();
	
	public Person getDriver() {
		if (partyThere != null) {
			return partyThere.getDriver();
		} else if (partyBack != null) {
			return partyBack.getDriver();
		} else {
			return null;
		}
	}
	
	public void setPartyThere(Party partyThere) throws Exception {
		if (this.getDriver() != null && this.getDriver() != partyThere.getDriver()) {
			throw new Exception("You cannot add a party with another driver to this touple!");
		}
		this.partyThere = partyThere;
	}
	
	public void setPartyBack(Party partyBack) throws Exception {
		if (this.getDriver() != null && this.getDriver() != partyBack.getDriver()) {
			throw new Exception("You cannot add a party with another driver to this touple!");
		}
		this.partyBack = partyBack;
	}
	
	public Party getPartyThere() {
		return partyThere;
	}
	
	public Party getPartyBack() {
		return partyBack;
	}
	
	public String toString() {
		return partyThere.toString() + "\n" + partyBack.toString();
	}

	public Set<Person> getPossibleDrivers() {
		return possibleDrivers;
	}

	public void setPossibleDrivers(Set<Person> possibleDrivers) {
		this.possibleDrivers = possibleDrivers;
	}
	
	public void addPossibleDriver(Person possibleDriver) {
		this.possibleDrivers.add(possibleDriver);
	}

	public boolean isDesignatedDriver() {
		return isDesignatedDriver;
	}

	public void setDesignatedDriver(boolean isDesignatedDriver) {
		this.isDesignatedDriver = isDesignatedDriver;
	}
	
}
