package com.thabok.entities;
import java.time.DayOfWeek;
import java.util.ArrayList;
import java.util.List;
import java.util.stream.Collectors;

public class Party {

	private DayOfWeek dayOfTheWeek;
	private boolean isWayBack;
	private Person driver;
	private List<Person> passengers = new ArrayList<>();

	public Person getDriver() {
		return driver;
	}

	public void setDriver(Person driver) {
		this.driver = driver;
	}

	public List<Person> getPassengers() {
		return passengers;
	}

	/**
	 * Sets passengers. If this list contains the driver he will be ignored
	 * @param passengers
	 * @throws Exception if you try to add too many people
	 */
	public void setPassengers(List<Person> passengers) throws Exception {
		this.passengers = passengers;
		try {
			if (this.passengers.contains(driver)) {
				this.passengers.remove(driver);
			}
		} catch (Exception e) {
		}
	}
	
	public void addPassenger(Person p) {
		this.passengers.add(p);
	}

	public DayOfWeek getDayOfTheWeek() {
		return dayOfTheWeek;
	}

	public void setDayOfTheWeek(DayOfWeek dayOfTheWeek) {
		this.dayOfTheWeek = dayOfTheWeek;
	}

	public boolean isWayBack() {
		return isWayBack;
	}

	public void setWayBack(boolean isWayBack) {
		this.isWayBack = isWayBack;
	}

	public String toString() {
		return (isWayBack ? "[<-] " : "[->] ")
				+ "[" + (isWayBack ? getLessonAsTwoCharacters(driver.schedule.getTimingInfoPerDay().get(dayOfTheWeek).getLastLesson()) : getLessonAsTwoCharacters(driver.schedule.getTimingInfoPerDay().get(dayOfTheWeek).getFirstLesson()) ) +  "] "
				+ driver.getName()
				+ (passengers.isEmpty() ? "" : " (" + String.join(", ", passengers.stream().map(p -> p.getName()).collect(Collectors.toList())) + ")");
	}
	
	private String getLessonAsTwoCharacters(int lesson) {
		if (lesson < 10) {
			return " " + lesson;
		} else {
			return "" + lesson;
		}
	}
}
